# Módulo para validación

import frappe
from erpnext_ec.utilities.doc_builder_tools import *
#from erpnext_ec.utilities.doc_render_tools import *

from erpnext_ec.utilities.doc_builder_fac import build_doc_fac 

@frappe.whitelist()
def validate_sales_invoice(doc_name):
    #Esta validacion servira para saber si el documento contiene toda la informacion necesaria para el SRI
    result = {}
    header = []
    alerts = []
    documentIsReady = True

    #doc = frappe.get_doc('Sales Invoice', doc_name)
    doc = build_doc_fac(doc_name)

    doctype_erpnext = 'Sales Invoice'
    typeDocSri = 'FAC'

    print(doctype_erpnext)
    print(doc)

    #sitenameVar = frappe.boot.sitename
    customer_email_id = ''

    #customerApi = get_full_customer_sri(doc.customer)
    #print(customerApi);

    #doc.paymentsItems = get_payments_sri(doc.name)    
    #doc.pagos = build_pagos(doc.paymentsItems)
    #paymentsApi = doc.paymentsItems

    if (doc.paymentsItems):
        alerts.append({"index": 0, "description": "No se han definido datos de pago (solicitud de pago/entrada de pago)", "type":"error"})
        documentIsReady = False
       
    if (doc.customer_tax_id == "" or doc.customer_tax_id == "9999999999"):
        alerts.append({"index": 0, "description": f"Cédula/Ruc del cliente es {doc.tax_id}", "type":"error"})

    print(doc.direccionComprador)
    if (doc.direccionComprador == None):            
        alerts.append({"index": 0, "description": "No se han definido datos de dirección del cliente", "type":"error"})
        documentIsReady = False    			

    if (doc.direccionComprador != None and (doc.customer_email_id == "" or doc.customer_email_id == None )):        
        alerts.append({"index": 0, "description": "No se ha definido Email del cliente", "type":"error"})
        documentIsReady = False    

    print(doc.estab)

    if (doc.estab == None or doc.estab == ''):
        alerts.append({"index": 0, "description": f"Establecimiento incorrecto ({doc.estab})", "type":"error"})
        documentIsReady = False    
    else:    
        alerts.append({"index": 0, "description": f"Establecimiento correcto ({doc.estab})", "type":"info"}) #green
    

    print(doc.ptoemi);

    if (doc.ptoemi == None or doc.ptoemi == ''):
        alerts.append({"index": 0, "description": f"Punto de emisión incorrecto ({doc.ptoemi})", "type":"error"})
        documentIsReady = False
    else:    
        alerts.append({"index": 0, "description": f"Punto de emisión correcto ({doc.ptoemi})", "type":"info"}) #green    

    header.append({"index": 0, "description": "Nombre cliente", "value":doc.customer_name})
    header.append({"index": 1, "description": "Tip.Doc. cliente", "value":doc.tipoIdentificacionComprador})
    header.append({"index": 2, "description": "Cédula/RUC cliente", "value":doc.customer_tax_id})
    header.append({"index": 3, "description": "Email cliente", "value":doc.customer_email_id})

    result = {
        "header": header,
        "alerts": alerts,
        "doctype_erpnext": doctype_erpnext,
        "typeDocSri": "typeDocSri",
        "documentIsReady": documentIsReady
    }

    return result