import json
from types import SimpleNamespace
from lxml import etree
from xml.etree.ElementTree import Element, SubElement, tostring
from datetime import datetime
from suds import WebFault
from suds.client import Client
from pprint import pformat
from OpenSSL import crypto
from random import randrange

import xmlsig
from xades import template,XAdESContext
from xades.policy import GenericPolicyId, ImpliedPolicy
import frappe
from frappe import _

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
#from cryptography.hazmat.backends import default_backend
#from cryptography.hazmat.primitives.serialization import load_pkcs12
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from cryptography import x509 as x509_crypt

#from cryptography import x509
from cryptography.hazmat.backends import default_backend
from erpnext_ec.utilities.xades_tool_v4 import sign_xml as sign_xml_xs

from requests import Session
import base64

import subprocess
import os
import uuid

class SriXmlData():
    
    def validate_password(self, sri_signature):
        #Se desencripta el password desde frappe para poder usarlo
        from frappe.utils.password import get_decrypted_password
        password_p12 = get_decrypted_password('Sri Signature', sri_signature.name, "password")

        #print(password_p12)

        #print(sri_signature.password)
        #password_p12 = 'beebtech2022CB'
        #password_p12 = sri_signature.password
        
        #full_path_p12 = '/opt/bench/frappe-bench/sites/principal/' + sri_signature.p12
        full_path_p12 = frappe.get_site_path() + sri_signature.p12
        
        try:
            with open(full_path_p12, "rb") as f:
                (
                    private_key,
                    p12,
                    additional_certificates,
                ) = serialization.pkcs12.load_key_and_certificates(
                    f.read() , password_p12.encode()
                    #, CLIENT_CERT_KEY.encode()
                )
                return private_key , p12
        except Exception as e:
            #print("Error validate_password:" + e)
            print(u"Error validate_password: %s", e)
            return None, None    
        
    def validate_password_old(self, sri_signature):
        #Se desencripta el password desde frappe para poder usarlo
        from frappe.utils.password import get_decrypted_password
        password_p12 = get_decrypted_password('Sri Signature', sri_signature.name, "password")

        #print(password_p12)
        
        #full_path_p12 = '/opt/bench/frappe-bench/sites/principal/' + sri_signature.p12
        full_path_p12 = frappe.get_site_path() + sri_signature.p12
        
        try:
            with open(full_path_p12, "rb") as f:
                p12 = f.read()                
                return p12
            
        except Exception as e:
            #print("Error validate_password:" + e)
            print(u"Error validate_password: %s", e)
            return None, None    

    def get_sri_signature(self, sri_signature_object):        
        if(sri_signature_object):
            sri_signature_validated, p12 = self.validate_password(self, sri_signature_object)            
            return sri_signature_validated, p12
        
    def get_sri_signature_from_json(self, doc):
        #print(doc)

        doc_object_build = json.loads(doc, object_hook=lambda d: SimpleNamespace(**d))
        
        #print(doc_object_build.name)

        #sri_signature = frappe.get_all('Sri Environment', fields='*', filters={'name': doc.sri_active_environment})        
        sri_signatures = frappe.get_all('Sri Signature', fields='*', filters={'name': doc_object_build.name})
        
        #print(sri_signatures)

        if(sri_signatures):

            sri_signature_object = sri_signatures[0]
            #sri_signature_validated = self.validate_password_old(self, sri_signature_object)
            sri_signature_validated, p12 = self.validate_password(self, sri_signature_object)
            
            return sri_signature_validated, p12
        
    def get_sri_signature_for_old(self, doc):
        #print(doc)

        #doc_object_build = json.loads(doc, object_hook=lambda d: SimpleNamespace(**d))
        
        sri_signatures = frappe.get_all('Sri Signature', fields='*', filters={'name': doc.name})
        
        print(sri_signatures)

        if(sri_signatures):

            sri_signature_object = sri_signatures[0]
            #sri_signature_validated = self.validate_password_old(self, sri_signature_object)
            p12 = self.validate_password_old(self, sri_signature_object)
            
            return p12
    
    def sign_xml_cmd(self, xml_string_data, signature_doc):
        
        nombre_temporal = str(uuid.uuid4())

        tmp_xml = frappe.get_site_path() + '/private/files/' + f'{nombre_temporal}.xml'
        output_xml = frappe.get_site_path() + '/private/files/' + f'{nombre_temporal}_signed.xml'

        with open(tmp_xml, "w") as text_file:
            text_file.write(xml_string_data)

        p12 = frappe.get_site_path() + signature_doc.p12        
        from frappe.utils.password import get_decrypted_password       
        password = get_decrypted_password('Sri Signature', signature_doc.name, "password")
        
        dir_path = os.path.dirname(os.path.realpath(__file__))

        # Nombre del archivo XSD
        appPath = dir_path + "/apps/XadesSignerCmd/XadesSignerCmd"
        tmpFolder = dir_path + "/apps/XadesSignerCmd/" 

        p = subprocess.Popen([appPath,
                              '--fileinput', tmp_xml ,
                              '--p12', p12,
                              '--password', password,
                              '--output', output_xml])

        res = p.communicate()

        #Leer XML Firmado
        file = open(output_xml, "r")
        content = file.read()
        #print(content)
        file.close()
        
        #En caso de usar firmas UANATACA
        #content = content.replace('organizationIdentifier=VATES-A66721499', '2.5.4.97=#0c0f56415445532d413636373231343939')

        try:
            os.remove(tmp_xml)
            os.remove(output_xml)
            #print("El archivo se ha eliminado exitosamente.")
        except FileNotFoundError:
            #print("El archivo no existe.")
            pass
        except Exception as e:
            #print("Ocurrió un error al intentar eliminar el archivo:", e)
            pass

        return content

    

    def sign_xml_xades(self, xml_string_data, sri_signature_object):
        
        #doc_object_build = json.loads(signature_doc, object_hook=lambda d: SimpleNamespace(**d))

        #sri_signatures = frappe.get_all('Sri Signature', fields='*', filters={'name': doc_object_build.name})
        
        #print(sri_signatures)        
        
        if(sri_signature_object):
            #sri_signature_object = sri_signatures[0]
            full_path_p12 = frappe.get_site_path() + sri_signature_object.p12
            #print(full_path_p12)
            from frappe.utils.password import get_decrypted_password
            password = get_decrypted_password('Sri Signature', sri_signature_object.name, "password")
            with open(full_path_p12, 'rb') as f:
                p12 = f.read()
                #print(pfx_data)

        password = password.encode()
        #print(type(xml_string_data))
        #print("---------------------------------------------------")
        signed = sign_xml_xs(p12, password, xml_string_data)

        #print("signed: ", signed)
        return signed

    def _clean_str(self, string_to_reeplace, list_characters=None):
        """
        Reemplaza caracteres por otros caracteres especificados en la lista
        @param string_to_reeplace:  string a la cual reemplazar caracteres
        @param list_characters:  Lista de tuplas con dos elementos(elemento uno el caracter a reemplazar, elemento dos caracter que reemplazara al elemento uno)
        @return: string con los caracteres reemplazados
        """
        if not string_to_reeplace:
            return string_to_reeplace
        caracters = ['.',',','-','\a','\b','\f','\n','\r','\t','\v']
        for c in caracters:
            string_to_reeplace = string_to_reeplace.replace(c, '')
        if not list_characters:
            list_characters=[(u'á','a'),(u'à','a'),(u'ä','a'),(u'â','a'),(u'Á','A'),(u'À','A'),(u'Ä','A'),(u'Â','A'),
                             (u'é','e'),(u'è','e'),(u'ë','e'),(u'ê','e'),(u'É','E'),(u'È','E'),(u'Ë','E'),(u'Ê','E'),
                             (u'í','i'),(u'ì','i'),(u'ï','i'),(u'î','i'),(u'Í','I'),(u'Ì','I'),(u'Ï','I'),(u'Î','I'),
                             (u'ó','o'),(u'ò','o'),(u'ö','o'),(u'ô','o'),(u'Ó','O'),(u'Ò','O'),(u'Ö','O'),(u'Ô','O'),
                             (u'ú','u'),(u'ù','u'),(u'ü','u'),(u'û','u'),(u'Ú','U'),(u'Ù','U'),(u'Ü','U'),(u'Û','U'),
                             (u'ñ','n'),(u'Ñ','N'),(u'/','-'), (u'&','Y'),(u'º',''), (u'´', '')]
        for character in list_characters:
            string_to_reeplace = string_to_reeplace.replace(character[0],character[1])
        SPACE = ' '
        #en range el ultimo numero no es inclusivo asi que agregarle uno mas
        #espacio en blanco
        range_ascii = [32]
        #numeros
        range_ascii += range(48, 57+1)
        #letras mayusculas
        range_ascii += range(65,90+1)
        #letras minusculas
        range_ascii += range(97,122+1)
        for c in string_to_reeplace:
            try:
                codigo_ascii = ord(c)
            except TypeError:
                codigo_ascii = False
            if codigo_ascii:
                #si no esta dentro del rang ascii reemplazar por un espacio
                if codigo_ascii not in range_ascii:
                    string_to_reeplace = string_to_reeplace.replace(c,SPACE)
            #si no tengo codigo ascii, posiblemente dio error en la conversion
            else:
                string_to_reeplace = string_to_reeplace.replace(c,SPACE)
        return ''.join(string_to_reeplace.splitlines())
