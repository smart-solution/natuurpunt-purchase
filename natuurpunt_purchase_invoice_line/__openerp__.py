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
    "name" : "Natuurpunt Purchase Invoice Line",
    "version" : "1.0",
    "author" : "fabian.semal@smartsolution.be",
    "website" : "www.smartsolution.be",
    "category" : "Purchase Management",
    "description": """ This module allows to add purchase order lines to invoice
    and to reset po lines when an invoice is deleted
""",
    "depends" : ["natuurpunt_purchase"],
    "data" : [
        'natuurpunt_purchase_invoice_line.xml',
        ],
    "active": False,
    "installable": True
}
