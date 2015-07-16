update purchase_approval_item a
set company_id = (
    select company_id
    from account_invoice inv
    where inv.id = a.invoice_id
)
where a.invoice_id is not null
    and company_id is null
;

update purchase_approval_item a
set company_id = (
    select company_id
    from purchase_order po
    where po.id = a.purchase_order_id
)
where a.purchase_order_id is not null
    and company_id is null
;

