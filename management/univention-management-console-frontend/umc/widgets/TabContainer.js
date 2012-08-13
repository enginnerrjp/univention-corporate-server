/*
 * Copyright 2011-2012 Univention GmbH
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
/*global define console*/

dojo.provide("umc.widgets.TabContainer");

dojo.require("dijit.layout.TabContainer");
dojo.require("tools");

/*REQUIRE:"dojo/_base/declare"*/ /*TODO*/return declare(dijit.layout.TabContainer, {
	// summary:
	//		An extended version of the dijit TabContainer that can hide/show tabs.

	_setVisibilityOfChild: function( child, visible ) {
		tools.assert( child.controlButton !== undefined, 'The widget is not attached to a TabContainer' );
		// we iterate over the children of the container to ensure the given widget is attached to THIS TabContainer
		/*REQUIRE:"dojo/_base/array"*/ array.forEach( this.getChildren(), function( item ) {
			if ( item == child ) {
				/*REQUIRE:"dojo/dom-class"*/ domClass.toggle( item.controlButton.domNode, 'dijitHidden', ! visible );
				return false;
			}
		} );
	},

	hideChild: function( child ) {
		this._setVisibilityOfChild( child, false );
	},

	showChild: function( child ) {
		this._setVisibilityOfChild( child, true );
	},

	startup: function() {
		this.inherited(arguments);

		// FIXME: Workaround for refreshing problems with datagrids when they are rendered
		//        on an inactive tab.

		// iterate over all tabs
		/*REQUIRE:"dojo/_base/array"*/ array.forEach(this.getChildren(), function(ipage) {
			// find all widgets that inherit from dojox.grid._Grid on the tab
			/*REQUIRE:"dojo/_base/array"*/ array.forEach(ipage.getDescendants(), function(iwidget) {
				if (tools.inheritsFrom(iwidget, 'dojox.grid._Grid')) {
					// hook to onShow event
					/*REQUIRE:"dojo/on"*/ /*TODO*/ this.own(this.on(ipage, 'onShow', function() {
						iwidget.startup();
					});
				}
			}, this);
		}, this);
	}
});


