# -*- coding: utf-8 -*-
##############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
############################################################################## 

{
    "name" : "natuurpunt_purchase_requisition",
    "version" : "1.0",
    "author" : "Natuurpunt (joeri.belis@natuurpunt.be)",
    "website" : "www.natuurpunt.be",
    "category" : "Purchase Management",
    "description": """
    This module allows you to manage your default user_id filter on Purchase Requisition.    

    The stock odoo module set a search_default_xxx filter on the view.
    using the uid of the logged in user. This custom module overrides this behaviour.
""",
    "depends" : ["purchase_requisition",],
    "data" : ["natuurpunt_purchase_requisition_view.xml"],
    "init_xml" : [],
    "update_xml" : [],
    "active": False,
    "installable": True
}
