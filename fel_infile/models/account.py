# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round

from datetime import datetime
import base64
from lxml import etree
import requests
import re

#from import XMLSigner

import logging

class AccountMove(models.Model):
    _inherit = "account.move"

    pdf_fel = fields.Char('PDF FEL', copy=False)

    def action_post(self):
        for move in self:
            if move.journal_id.usuario_fel and move.requiere_certificacion():

                if move.error_pre_validacion():
                    return
                
                dte = move.dte_documento()
                logging.warn(dte)
                xmls = etree.tostring(dte, encoding="UTF-8")
                # xmls = xmls.decode("utf-8").replace("&amp;", "&").encode("utf-8")
                xmls_base64 = base64.b64encode(xmls)
                logging.warn(xmls)

                headers = { "Content-Type": "application/json" }
                data = {
                    "llave": move.journal_id.token_firma_fel,
                    "archivo": xmls_base64.decode("utf-8"),
                    "codigo": move.company_id.vat.replace('-',''),
                    "alias": move.journal_id.usuario_fel,
                }
                r = requests.post('https://signer-emisores.feel.com.gt/sign_solicitud_firmas/firma_xml', json=data, headers=headers)
                logging.warn(r.text)
                firma_json = r.json()
                if firma_json["resultado"]:

                    headers = {
                        "USUARIO": move.journal_id.usuario_fel,
                        "LLAVE": move.journal_id.clave_fel,
                        "IDENTIFICADOR": move.journal_id.code + str(move.id),
                        "Content-Type": "application/json",
                    }
                    data = {
                        "nit_emisor": move.company_id.vat.replace('-',''),
                        "correo_copia": move.company_id.email,
                        "xml_dte": firma_json["archivo"]
                    }
                    r = requests.post("https://certificador.feel.com.gt/fel/certificacion/v2/dte/", json=data, headers=headers)
                    logging.warn(r.json())
                    certificacion_json = r.json()
                    if certificacion_json["resultado"]:
                        move.firma_fel = certificacion_json["uuid"]
                        move.name = str(certificacion_json["serie"]) + "-" + str(certificacion_json["numero"])
                        move.serie_fel = certificacion_json["serie"]
                        move.numero_fel = certificacion_json["numero"]
                        move.documento_xml_fel = xmls_base64
                        move.resultado_xml_fel = certificacion_json["xml_certificado"]
                        move.pdf_fel = "https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid=" + certificacion_json["uuid"]
                    else:
                        move.error_certificador(str(certificacion_json["descripcion_errores"]))
                        return

                else:
                    move.error_certificador(r.text)
                    return
                        
                return super(AccountMove, self).action_post()

            else:
                return super(AccountMove, self).action_post()

    def button_cancel(self):
        result = super(AccountMove, self).button_cancel()
        if result:
            for move in self:
                if move.journal_id.usuario_fel and move.requiere_certificacion():
                    dte = move.dte_anulacion()
                    xmls = etree.tostring(dte, encoding="UTF-8")
                    # xmls = xmls.decode("utf-8").replace("&amp;", "&").encode("utf-8")
                    xmls_base64 = base64.b64encode(xmls)
                    logging.warn(xmls)

                    headers = { "Content-Type": "application/json" }
                    data = {
                        "llave": move.journal_id.token_firma_fel,
                        "archivo": xmls_base64.decode("utf-8"),
                        "codigo": move.company_id.vat.replace('-',''),
                        "alias": move.journal_id.usuario_fel,
                        "es_anulacion": "S",
                    }
                    r = requests.post('https://signer-emisores.feel.com.gt/sign_solicitud_firmas/firma_xml', json=data, headers=headers)
                    logging.warn(r.text)
                    firma_json = r.json()
                    if firma_json["resultado"]:

                        headers = {
                            "USUARIO": move.journal_id.usuario_fel,
                            "LLAVE": move.journal_id.clave_fel,
                            "IDENTIFICADOR": move.journal_id.code + str(move.id),
                            "Content-Type": "application/json",
                        }
                        data = {
                            "nit_emisor": move.company_id.vat.replace('-',''),
                            "correo_copia": move.company_id.email,
                            "xml_dte": firma_json["archivo"]
                        }
                        r = requests.post("https://certificador.feel.com.gt/fel/anulacion/v2/dte/", json=data, headers=headers)
                        logging.warn(r.text)
                        certificacion_json = r.json()
                        if not certificacion_json["resultado"]:
                            raise UserError(str(certificacion_json["descripcion_errores"]))

                    else:
                        raise UserError(r.text)

class AccountJournal(models.Model):
    _inherit = "account.journal"

    usuario_fel = fields.Char('Usuario FEL', copy=False)
    clave_fel = fields.Char('Clave FEL', copy=False)
    token_firma_fel = fields.Char('Token Firma FEL', copy=False)