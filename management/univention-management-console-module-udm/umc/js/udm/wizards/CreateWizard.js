/*
 * Copyright 2013 Univention GmbH
 *
 * http://www.univention.de/
 *
 * All rights reserved.
 *
 * The source code of this program is made available
 * under the terms of the GNU Affero General Public License version 3
 * (GNU AGPL V3) as published by the Free Software Foundation.
 *
 * Binary versions of this program provided by Univention to you as
 * well as other copyrighted, protected or trademarked materials like
 * Logos, graphics, fonts, specific documentations and configurations,
 * cryptographic keys etc. are subject to a license agreement between
 * you and Univention and not subject to the GNU AGPL V3.
 *
 * In the case you use this program under the terms of the GNU AGPL V3,
 * the program is provided in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License with the Debian GNU/Linux or Univention distribution in file
 * /usr/share/common-licenses/AGPL-3; if not, see
 * <http://www.gnu.org/licenses/>.
 */
/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"umc/tools",
	"umc/widgets/Wizard",
	"umc/i18n!umc/modules/udm"
], function(declare, lang, array, tools, Wizard, _) {

	return declare("umc.modules.udm.wizards.CreateWizard", [ Wizard ], {
		autoValidate: true,
		autoFocus: true,

		detailPage: null,

		widgetPages: null,

		_getPageWidgets: function(layout) {
			var widgets = [];
			array.forEach(layout, function(row) {
				widgets = widgets.concat(row);
			});
			return widgets;
		},

		buildWidget: function(widgetName, originalWidgetDefinition) {
			if (originalWidgetDefinition.multivalue) {
				this._multiValuesWidgets.push(widgetName);
				originalWidgetDefinition = lang.clone(originalWidgetDefinition);
				originalWidgetDefinition.type = 'TextBox';
			}
			return {
				name: widgetName,
				sizeClass: originalWidgetDefinition.size,
				label: originalWidgetDefinition.label,
				required: originalWidgetDefinition.required,
				type: originalWidgetDefinition.type
			};
		},

		getValues: function() {
			var values = this.inherited(arguments);
			tools.forIn(lang.clone(values), lang.hitch(this, function(key, value) {
				if (this._multiValuesWidgets.indexOf(key) !== -1) {
					values[key] = [value];
				}
			}));
			return values;
		},

		postMixInProperties: function() {
			this.inherited(arguments);
			this._mayFinishDeferred = this.detailPage.loadedDeferred;
			this._detailButtons = this.detailPage.getButtonDefinitions();
			this._multiValuesWidgets = [];
			var pages = [];
			this._connectWidgets = [];
			array.forEach(this.widgetPages, lang.hitch(this, function(page) {
				var layout = page.widgets;
				var widgets = [];
				var pageName = 'page' + pages.length;
				var pageWidgets = this._getPageWidgets(layout);
				array.forEach(pageWidgets, lang.hitch(this, function(widgetName) {
					var originalWidgetDefinition = array.filter(this.properties, function(prop) { return prop.id == widgetName; })[0];
					widgets.push(this.buildWidget(widgetName, originalWidgetDefinition));
					this._connectWidgets.push({page: pageName, widget: widgetName});
				}));
				pages.push({
					name: pageName,
					headerText: page.title,
					helpText: page.helpText,
					widgets: widgets,
					layout: layout
				});
			}));
			lang.mixin(this, {
				pages: pages
			});
		},

		buildRendering: function() {
			this.inherited(arguments);
			var allWidgets = {};
			tools.forIn(this._pages, lang.hitch(this, function(pageName, page) {
				var finishButton = page._footerButtons.finish;
				var originalLabel = finishButton.get('label');
				finishButton.set('disabled', true);
				finishButton.set('label', this.detailPage.progressMessage);
				this._mayFinishDeferred.then(function() {
					finishButton.set('label', originalLabel);
					finishButton.set('disabled', false);
				});
				lang.mixin(allWidgets, page._form._widgets);
			}));

			this.templateObject = this.detailPage.buildTemplate(this.template, this.properties, allWidgets);
			this.own(this.templateObject);
		},

		getFooterButtons: function() {
			var buttons = this.inherited(arguments);
			array.forEach(buttons, lang.hitch(this, function(button) {
				if (button.name === 'finish') {
					array.some(this._detailButtons, function(detailButton) {
						if (detailButton.name === 'submit') {
							button.label = detailButton.label;
							return true;
						}
					});
				}
			}));
			buttons.unshift({
				name: 'advance',
				label: _('Advanced'),
				align: 'right',
				callback: lang.hitch(this, function() {
					this.onAdvanced(this.getValues());
				})
			});
			return buttons;
		},

		canFinish: function() {
			return this.inherited(arguments) && this._mayFinishDeferred.isResolved();
		},

		onAdvanced: function() {
		}
	});
});

