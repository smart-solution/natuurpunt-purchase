# -*- coding: utf-8 -*-
##############################################################################
#
#    Smart Solution bvba
#    Copyright (C) 2010-Today Smart Solution BVBA (<http://www.smartsolution.be>).
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
    "name" : "natuurpunt_purchase_small_changes",
    "version" : "1.0",
    "author" : "Natuurpunt (mattias.vanopstal@natuurpunt.be)",
    "website" : "www.natuurpunt.be",
    "category" : "Purchase Management",
    "description": """ This module collects all small changes related to 
    purchase management modules
""",
    "depends" : ["natuurpunt_purchase_search",
                 "natuurpunt_purchase_requisition",
                 "multi_analytical_account"],
    "data" : [
        'natuurpunt_purchase_small_changes_view.xml',
        ],
    "active": False,
    "installable": True
}
