INSERT INTO dim_vendor (vendor_id, vendor_name) VALUES
(1, 'Creative Mobile Technologies, LLC'),
(2, 'Curb Mobility, LLC'),
(6, 'Myle Technologies Inc'),
(7, 'Helix')
ON CONFLICT (vendor_id) DO NOTHING;

INSERT INTO dim_ratecode (ratecode_id, ratecode_label) VALUES
(1, 'Standard rate'),
(2, 'JFK'),
(3, 'Newark'),
(4, 'Nassau or Westchester'),
(5, 'Negotiated fare'),
(6, 'Group ride'),
(99, 'Null / Unknown')
ON CONFLICT (ratecode_id) DO NOTHING;


INSERT INTO dim_payment_type (payment_type_id, payment_label) VALUES
(0, 'Flex Fare'),
(1, 'Credit card'),
(2, 'Cash'),
(3, 'No charge'),
(4, 'Dispute'),
(5, 'Unknown'),
(6, 'Voided trip')
ON CONFLICT (payment_type_id) DO NOTHING;

