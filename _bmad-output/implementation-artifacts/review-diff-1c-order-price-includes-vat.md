# Review Diff: 1C Order Price Includes VAT

Baseline commit: `c04316a913cc944307f7ff4d03e22ee1b12a5d33`

Changed files:

- `backend/apps/orders/services/order_export.py`
- `backend/tests/unit/test_order_export_service.py`
- `docs/integrations/1c/order-vat-warehouse-routing.md`
- `docs/integrations/1c/samples/order-export-org-warehouse-diagnostic.xml`

Verification already run:

- `docker compose --env-file ..\.env -f ..\docker\docker-compose.yml exec -T backend pytest tests/unit/test_order_export_service.py -k "summe or stavka_22_in_item"` -> `2 passed, 60 deselected`
- `rg -n "УчтеноВСумме" apps/orders/services/order_export.py tests/unit/test_order_export_service.py ..\docs\integrations\1c` -> new tag present in code, test, docs
- `rg -n "УчтенВСумме" apps/orders/services/order_export.py ..\docs\integrations\1c` -> no matches

Unified diff:

```diff
diff --git a/backend/apps/orders/services/order_export.py b/backend/apps/orders/services/order_export.py
index a9ddfee9..fa66aa77 100644
--- a/backend/apps/orders/services/order_export.py
+++ b/backend/apps/orders/services/order_export.py
@@ -372,7 +372,8 @@ class OrderExportService:
             taxes = ET.SubElement(product, "Налоги")
             tax = ET.SubElement(taxes, "Налог")
             self._add_text_element(tax, "Наименование", "НДС")
-            self._add_text_element(tax, "УчтенВСумме", "true")
+            # CommerceML/Bitrix expects the standard "included in sum" flag name.
+            self._add_text_element(tax, "УчтеноВСумме", "true")
             self._add_text_element(tax, "Ставка", str(int(item_vat_rate)))
             self._add_text_element(tax, "Сумма", self._format_price(vat_amount))
 
diff --git a/backend/tests/unit/test_order_export_service.py b/backend/tests/unit/test_order_export_service.py
index 83941240..16af0688 100644
--- a/backend/tests/unit/test_order_export_service.py
+++ b/backend/tests/unit/test_order_export_service.py
@@ -1983,8 +1983,8 @@ class TestOrderExportVatAndOrgInXML:
         assert vid_ceny_name is not None
         assert vid_ceny_name.text == "РРЦ"
 
-    def test_nds_uchten_v_summe_true(self, settings):
-        """Each <Товар> has <Налоги> with <УчтенВСумме>true</УчтенВСумме>."""
+    def test_nds_uchteno_v_summe_true_and_gross_price_preserved(self, settings):
+        """Each <Товар> marks VAT as included in sum without changing gross unit price."""
         settings.ONEC_EXCHANGE = {
             **settings.ONEC_EXCHANGE,
             "DEFAULT_VAT_RATE": 22,
@@ -1995,9 +1995,14 @@ class TestOrderExportVatAndOrgInXML:
         xml_str = service.generate_xml(Order.objects.filter(id=order.id))
         root = ET.fromstring(xml_str)
 
-        uchten = root.find(".//Товар/Налоги/Налог/УчтенВСумме")
-        assert uchten is not None
-        assert uchten.text == "true"
+        unit_price = root.find(".//Товар/ЦенаЗаЕдиницу")
+        assert unit_price is not None
+        assert unit_price.text == "2109.00"
+
+        uchteno = root.find(".//Товар/Налоги/Налог/УчтеноВСумме")
+        assert uchteno is not None
+        assert uchteno.text == "true"
+        assert root.find(".//Товар/Налоги/Налог/УчтенВСумме") is None
 
     def test_nds_stavka_22_in_item(self, settings):
         """НДС ставка 22% correctly exported in <Ставка>22</Ставка>."""
diff --git a/docs/integrations/1c/order-vat-warehouse-routing.md b/docs/integrations/1c/order-vat-warehouse-routing.md
index aa831c5d..f4ae9f97 100644
--- a/docs/integrations/1c/order-vat-warehouse-routing.md
+++ b/docs/integrations/1c/order-vat-warehouse-routing.md
@@ -164,7 +164,7 @@ vat_group sub-order
 - `Соглашение`;
 - товарные строки с `Ид`, `Наименование`, `ЦенаЗаЕдиницу`, `Количество`, `Сумма`;
 - `ВидЦены/Ид` и `ВидЦены/Наименование`;
- блок `Налоги/Налог` со ставкой и суммой НДС;
+ блок `Налоги/Налог` со ставкой, суммой НДС и тегом `УчтеноВСумме=true`, то есть `ЦенаЗаЕдиницу` уже включает НДС и не должна пересчитываться в 1С как цена без налога;
 - обязательные реквизиты УТ 11, включая `Организация`, `Склад`, `Соглашение`, `Операция`, `Статус заказа`.
 
 ## Проверочный сценарий 78 + 4441 + 4925
diff --git a/docs/integrations/1c/samples/order-export-org-warehouse-diagnostic.xml b/docs/integrations/1c/samples/order-export-org-warehouse-diagnostic.xml
index 08eb3de9..de36528a 100644
--- a/docs/integrations/1c/samples/order-export-org-warehouse-diagnostic.xml
+++ b/docs/integrations/1c/samples/order-export-org-warehouse-diagnostic.xml
@@ -36,7 +36,7 @@
           <Налоги>
             <Налог>
               <Наименование>НДС</Наименование>
-              <УчтенВСумме>true</УчтенВСумме>
+              <УчтеноВСумме>true</УчтеноВСумме>
               <Ставка>22</Ставка>
               <Сумма>18.03</Сумма>
             </Налог>
@@ -99,7 +99,7 @@
           <Налоги>
             <Налог>
               <Наименование>НДС</Наименование>
-              <УчтенВСумме>true</УчтенВСумме>
+              <УчтеноВСумме>true</УчтеноВСумме>
               <Ставка>5</Ставка>
               <Сумма>4.76</Сумма>
             </Налог>
```
