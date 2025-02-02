# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round

import requests

import logging

class Partner(models.Model):
    _inherit = 'res.partner'

    def obtener_nombre_facturacion_fel(self):
        vat = self.vat
        if self.nit_facturacion_fel:
            vat = self.nit_facturacion_fel
            
        res = self._datos_sat(self.env.company, vat)
        self.nombre_facturacion_fel = res['nombre']
    
    def _datos_sat(self, company, vat):
        if vat:
            headers = { "Content-Type": "application/json" }
            data = {
                "emisor_codigo": company.usuario_fel,
                "emisor_clave": company.clave_fel,
                "nit_consulta": vat.replace('-',''),
            }
            r = requests.post('https://consultareceptores.feel.com.gt/rest/action', json=data, headers=headers)
            logging.warning(r.text)
            if r and r.json():
                return r.json()
                
        return {'nombre': '', 'nit': ''}
