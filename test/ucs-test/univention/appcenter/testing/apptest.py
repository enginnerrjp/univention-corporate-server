#!/usr/bin/python3
from contextlib import contextmanager
import os
import os.path
import datetime
import logging
import time
import subprocess
import sys
import importlib
import tempfile
import shutil
from http.client import HTTPConnection
import pathlib

logger = logging.getLogger(__name__)

def run_test_file(fname):
	with tempfile.NamedTemporaryFile(suffix='.py') as tmpfile:
		logger.info('Copying file to {}'.format(tmpfile.name))
		shutil.copy2(fname, tmpfile.name)
		if 'UCS_TEST_SESSION_NAME' not in os.environ:
			os.environ['UCS_TEST_SESSION_NAME'] = os.path.basename(tmpfile.name)
		with pip_modules(['pytest', 'selenium', 'xvfbwrapper', 'uritemplate']):
			importlib.reload(sys.modules[__name__])
			import pytest
			test_func = os.environ.get('UCS_TEST_ONE_TEST')
			if test_func:
				sys.exit(pytest.main([tmpfile.name + '::' + test_func, '-p', __name__, '-x', '--pdb']))
			else:
				pass
				sys.exit(pytest.main([tmpfile.name, '-p', __name__]))

@contextmanager
def pip_modules(modules):
	if os.environ.get('UCS_TEST_NO_PIP') == 'TRUE':
		yield
	if subprocess.run(['which', 'pip3'], stdout=subprocess.DEVNULL).returncode != 0:
		raise RuntimeError('pip3 is required. Install python3-pip')
	installed = subprocess.run(['pip3', 'list', '--format=columns'], stdout=subprocess.PIPE)
	logger.info(modules)
	for line in installed.stdout.splitlines()[2:]:
		mod, ver = line.decode('utf-8').strip().split()
		if mod in modules:
			modules.remove(mod)
		if '{}=={}'.format(mod, ver) in modules:
			modules.remove('{}=={}'.format(mod, ver))
	logger.info(modules)
	if modules:
		logger.info('Installing modules via pip3')
		logger.info('  {}'.format(' '.join(modules)))
		subprocess.check_output(['pip3', 'install'] + modules)
	try:
		yield
	finally:
		if modules:
			logger.info('Uninstalling modules via pip3')
			subprocess.check_output(['pip3', 'uninstall', '--yes'] + modules)

@contextmanager
def xserver(capture_video=None):
	if os.environ.get('DISPLAY'):
		yield
	else:
		from xvfbwrapper import Xvfb
		with Xvfb(width=1920, height=1080) as xvfb:
			time.sleep(2)
			if capture_video:
				pid = ffmpg_start(capture_video, xvfb.vdisplay_num)
			time.sleep(2)
			yield
			if capture_video:
				ffmpg_stop(pid)
		if 'DISPLAY' in os.environ:
			# work around xvfb setting DISPLAY to :0 here
			# so that a second xserver() would not go into this else
			# clause, causing problems as no xserver is running
			del os.environ['DISPLAY']

def ffmpg_start(capture_video, display):
	process = subprocess.Popen(['ffmpeg', '-y', '-f', 'x11grab', '-video_size', '1920x1080', '-i', ':{}'.format(display), capture_video], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	return process.pid

def ffmpg_stop(pid):
	subprocess.run(['kill', str(pid)])

class Session(object):
	def __init__(self, name, base_url, screenshot_path, driver):
		self.name = name
		self.base_url = base_url
		self.screenshot_path = screenshot_path
		self.driver = driver

	def __enter__(self):
		yield self

	def __exit__(self, exc_type, exc_value, traceback):
		try:
			self.save_screenshot()
		finally:
			self.driver.quit()

	def __del__(self):
		self.driver.quit()

	def goto_portal(self):
		self.get('/univention/portal')
		time.sleep(2)
		self.click_element('#umc_menu_Button_0')
		time.sleep(1)
		self.click_element('#umcMenuLanguage')
		time.sleep(1)
		for element in self.find_all('#umcMenuLanguage__slide .menuItem'):
			if element.text == 'English':
				element.click()
				time.sleep(2)
				break

	def click_portal_tile(self, name):
		elements = self.find_all('.umcGalleryNameContent')
		for element in elements:
			if element.text == name:
				self.driver.execute_script("arguments[0].click();", element)
				break
		else:
			raise RuntimeError('Could not find {}'.format(name))

	@contextmanager
	def switched_frame(self, css):
		iframe = self.assert_one(css)
		self.driver.switch_to.frame(iframe)
		yield
		self.driver.switch_to.default_content()

	def get(self, url):
		if url.startswith('/'):
			url = self.base_url + url
		self.driver.get(url)

	def reload(self):
		self.driver.refresh()

	def find_all(self, css):
		logger.info("Searching for %r", css)
		return self.driver.find_elements_by_css_selector(css)

	def find_all_below(self, element, css):
		return element.find_elements_by_css_selector(css)

	def find_first(self, css):
		elements = self.find_all(css)
		logger.info("Found %d elements", len(elements))
		if len(elements) == 0:
			return None
		return elements[0]

	def assert_one(self, css):
		elements = self.find_all(css)
		assert len(elements) == 1, 'len(elements) == {}'.format(len(elements))
		return elements[0]

	def assert_one_below(self, element, css):
		elements = self.find_all_below(element, css)
		assert len(elements) == 1, 'len(elements) == {}'.format(len(elements))
		return elements[0]

	def click_element(self, css):
		self.assert_one(css).click()

	def click_element_below(self, element, css):
		self.assert_one_below(element, css).click()

	def change_tab(self, idx):
		self.driver.switch_to.window(self.driver.window_handles[idx])

	def close_tab(self):
		self.driver.close()

	def enter_input(self, input_name, value):
		self.enter_input_element('[name={}]'.format(input_name), value)

	def enter_input_element(self, css, value):
		from selenium.common.exceptions import InvalidElementStateException
		elem = self.assert_one(css)
		try:
			elem.clear()
		except InvalidElementStateException:
			pass
		elem.send_keys(value)

	def enter_return(self, css=None):
		from selenium.webdriver.common.keys import Keys
		if css:
			self.enter_input_element(css, Keys.RETURN)
		else:
			self.send_keys(Keys.RETURN)

	def send_keys(self, keys):
		from selenium.webdriver import ActionChains
		action = ActionChains(self.driver)
		action.send_keys(keys).perform()

	def save_screenshot(self, name=None):
		name = name or self.name
		timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
		os.makedirs(self.screenshot_path, exist_ok=True)
		filename = os.path.join(self.screenshot_path, '%s_%s.png' % (name, timestamp))
		logger.info('Saving screenshot %r', filename)
		self.driver.save_screenshot(filename)

	@classmethod
	def chrome(cls, name, base_url, screenshot_path):
		from selenium import webdriver
		options = webdriver.ChromeOptions()
		options.add_argument('--no-sandbox')  # chrome complains about being executed as root
		driver = webdriver.Chrome(options=options)
		return cls(name, base_url, screenshot_path, driver)

	@classmethod
	@contextmanager
	def running_chrome(cls, name, base_url, screenshot_path):
		with xserver(str(pathlib.Path(screenshot_path) / '{}.mkv'.format(name))):
			obj = cls.chrome(name, base_url, screenshot_path)
			with obj:
				yield obj

try:
	import pytest
except ImportError:
	pass
else:
	@pytest.fixture(scope='session')
	def config():
		"""Test wide Configuration aka UCR
		Used to get some defaults if not environment variables are
		given. But if UCR is not avaiable, returns an empty dict...
		"""
		try:
			from univention.config_registry import ConfigRegistry
			ucr = ConfigRegistry()
			ucr.load()
			return dict(ucr)
		except ImportError:
			return {}

	@pytest.fixture(scope='session')
	def hostname(config):
		"""Hostname to test against"""
		ret = os.environ.get('UCS_TEST_HOSTNAME')
		if ret is None:
			if config:
				ret = 'https://{hostname}.{domainname}'.format(**config)
			else:
				logger.warning('$UCS_TEST_HOSTNAME not set')
				ret = 'http://localhost'
		return ret

	@pytest.fixture(scope='session')
	def admin_username(config):
		"""Username of the Admin account"""
		ret = os.environ.get('UCS_TEST_ADMIN_USERNAME')
		if not ret:
			ret = config.get('tests/domainadmin/account')
			if ret:
				ret = ret.split(',')[0].split('=')[-1]
			else:
				ret = 'Administrator'
		return ret

	@pytest.fixture(scope='session')
	def admin_password(config):
		"""Password of the Admin account"""
		ret = os.environ.get('UCS_TEST_ADMIN_USERNAME')
		ret = os.environ.get('UCS_TEST_ADMIN_PASSWORD')
		if not ret:
			ret = config.get('tests/domainadmin/pwd', 'univention')
		return ret

	@pytest.fixture(scope='session')
	def umc(hostname, admin_username, admin_password):
		umc_lib = os.environ.get('UCS_TEST_UMC_CLIENT_LIB', 'univention.testing._umc')
		try:
			umc_lib = importlib.import_module(umc_lib)
		except ImportError:
			logger.critical('Could not import {}. Maybe set $UCS_TEST_UMC_CLIENT_LIB'.format(umc_lib))
			raise
		Client = umc_lib.Client
		scheme, hostname = hostname.split('//')
		if scheme == 'http:':
			Client.ConnectionType = HTTPConnection
		client = Client(hostname=hostname, username=admin_username, password=admin_password, useragent='UCS/ucs-test')
		return client

	@pytest.fixture(scope='session')
	def appcenter(umc):
		class AppCenter(object):
			def __init__(self, client):
				self.client = client

			def install_newest(self, app_id):
				app = self.get(app_id)
				app_function = None
				if app['is_installed']:
					logger.info('App already installed')
					if 'candidate_version' in app:
						logger.info('Upgrading App...')
						app_function = 'update'
				else:
					logger.info('Installing App...')
					app_function = 'install'
				if not app_function:
					return app
				if app['docker_image'] or app['docker_main_service']:
					logger.info('Installing Docker App')
					response = self.client.umc_command('appcenter/docker/invoke', {
						'app': app_id,
						'function': app_function,
						'force': True,
						})
					progress_id = response.result['id']
					progress_command = 'appcenter/docker/progress'
				else:
					logger.info('Installing Non-Docker App')
					response = self.client.umc_command('appcenter/invoke', {
						'application': app_id,
						'function': app_function,
						'only_dry_run': False,
						})
					progress_id = response.result['id']
					progress_command = 'appcenter/progress'
				finished = False
				i = 0
				while not finished:
					time.sleep(2)
					i += 1
					if i > 600:
						raise RuntimeError('Did not finish within 20 minutes')
					result = self.client.umc_command(progress_command, {'progress_id': progress_id}).result
					finished = result.get('finished')
					assert not result.get('serious_problems')
					for message in result.get('intermediate', []):
						logger.info(message)
				app = self.get(app_id)
				assert app['is_installed']
				return app

			def get(self, app_id):
				logger.info('Retrieving App {}'.format(app_id))
				response = self.client.umc_command('appcenter/get', {'application': app_id})
				return response.result

		return AppCenter(umc)

	@pytest.fixture(scope='session')
	def udm(hostname, config, admin_username, admin_password):
		"""A UDM instance (REST client)"""
		rest_lib = os.environ.get('UCS_TEST_REST_CLIENT_LIB', 'univention.testing._udm_rest')
		try:
			rest_lib = importlib.import_module(rest_lib)
		except ImportError:
			logger.critical('Could not import {}. Maybe set $UCS_TEST_REST_CLIENT_LIB'.format(rest_lib))
			raise
		uri = os.environ.get('UCS_TEST_UDM_URI')
		if not uri:
			if config:
				hostname = 'https://{}'.format(config.get('ldap/master'))
			else:
				logger.warning('$UCS_TEST_UDM_URI not set')
			uri = '{}/univention/udm/'.format(hostname)
		udm = rest_lib.UDM.http(uri, admin_username, admin_password)
		return udm

	@pytest.fixture(scope='session')
	def users(udm):
		user_mod = udm.get('users/user')
		users = {}
		user_id_cache = {'X': 1}  # very elegant...
		def _users(user_id=None, attrs={}):
			username = attrs.get('username')
			if username is None:
				if user_id is None:
					user_id = user_id_cache['X']
					user_id_cache['X'] += 1
				username = 'ucs-test-user-{}'.format(user_id)
			if username not in users:
				user = user_mod.new()
				user.properties.update(attrs)
				if user.properties['username'] is None:
					user.properties['username'] = username
				if user.properties['firstname'] is None:
					user.properties['firstname'] = 'John'
				if user.properties['lastname'] is None:
					user.properties['lastname'] = user.properties['username']
				if user.properties['password'] is None:
					user.properties['password'] = 'univention'
				user.save()
				users[username] = user
			else:
				if attrs:
					user = users[username]
					user.reload()
					user.properties.update(attrs)
					user.save()
			user = users[username]
			user.reload()
			return user
		try:
			yield _users
		finally:
			for user in users.values():
				user.delete()

	@pytest.fixture
	def new_user(users):
		"""Creates a new user and cleans up"""
		user = users()
		return user

	@pytest.fixture(scope='session')
	def db_conn():
		"""A database connection object (sqlalchemy)"""
		import sqlalchemy
		ret = os.environ.get('UCS_TEST_DB_URI')
		if not ret:
			logger.warning('$UCS_TEST_DB_URI not set')
			raise ValueError('Need $UCS_TEST_DB_URI')
		engine = sqlalchemy.create_engine(ret)
		with engine.connect() as conn:
			yield conn

	@pytest.fixture(scope='session')
	def selenium_base_url(hostname):
		"""Base URL for selenium"""
		ret = os.environ.get('UCS_TEST_SELENIUM_BASE_URL')
		if ret is None:
			logger.warning('$UCS_TEST_SELENIUM_BASE_URL not set')
			ret = hostname
			logger.warning('  using {}'.format(ret))
		return ret

	@pytest.fixture(scope='session')
	def selenium_screenshot_path():
		"""Path where selenium should save screenshots"""
		ret = os.environ.get('UCS_TEST_SELENIUM_SCREENSHOT_PATH')
		if ret is None:
			logger.warning('$UCS_TEST_SELENIUM_SCREENSHOT_PATH not set')
			ret = 'selenium'
			logger.warning('  using {}'.format(ret))
		return ret

	@pytest.fixture
	def chrome(selenium_base_url, selenium_screenshot_path):
		"""A running chrome instance, controllable by selenium"""
		name = os.environ.get('UCS_TEST_SESSION_NAME') or 'test'
		with Session.running_chrome(name, selenium_base_url, selenium_screenshot_path) as c:
			yield c
