# V8 Workflow Guide: Looker-First Product Matching

## 🎯 What Changed in V8?

**V7 (Old):**
```
main.py → Phase 1 (Discovery) → Phase 2 (Items) → Phase 3 (Match ALL items)
```

**V8 (New):**
```
main.py → Phase 1 (Discovery) → Phase 2 (Items) → Done!
                                                     ↓
                                          Explore in Looker Studio
                                                     ↓
                                          Run ai_matching/ for specific products
```

---

## ✅ Benefits

| Aspect | V7 | V8 |
|--------|-----|-----|
| **Daily run time** | ~15 minutes | ~10 minutes |
| **Match quality** | 30% (fuzzy) | 70% (AI) |
| **Control** | Match everything | Match only what you want |
| **Cost** | Free (but low quality) | ~$0.02 per category |
| **Workflow** | Automated | Explore → Match |

---

## 📋 Step-by-Step Workflow

### **Step 1: Daily Data Collection**

Run main.py to collect tender data (Phase 3 SKIPPED by default):

```bash
# Standard daily run (fast - no matching)
python3 main.py --start 20250101 --end 20250131 --states SP RJ MG

# Optional: Enable Phase 3 if you want fuzzy matching
python3 main.py --start 20250101 --end 20250131 --states SP --match
```

**Result:** All tenders and items saved to database, ready for Looker exploration.

---

### **Step 2: Explore Data in Looker Studio**

1. **Connect Looker Studio to Cloud SQL**
   - Follow instructions in `LOOKER_STUDIO_GUIDE.md`

2. **Create views using `looker_views.sql`**
   ```bash
   # In Cloud SQL console, run:
   psql -h <your-db-host> -U postgres -d pncp_medical_data -f looker_views.sql
   ```

3. **Explore in Looker Studio**
   - Use `vw_curativos` - See all wound care products
   - Use `vw_mdsap_items` - See MDSAP-relevant items
   - Use `vw_high_value_items` - See high-value opportunities
   - Use `vw_items_by_state` - See geographic distribution

4. **Identify interesting product categories**
   - Look for patterns in item descriptions
   - Find categories worth matching to your catalog
   - Note the keywords used (e.g., "curativo", "transparente", "filme")

---

### **Step 3: Update Keywords**

Edit `keywords.json` with products you want to match:

```json
{
  "keywords": [
    "curativo",
    "transparente",
    "filme",
    "gaze",
    "compressa",
    "bandagem"
  ]
}
```

**Tip:** Start with 2-3 keywords, test the match quality, then add more.

---

### **Step 4: Run AI Matching**

```bash
# Step 1: Extract items matching your keywords
python3 ai_matching/step1_extract_keywords.py

# Output: data/filtered_items_for_matching.json
# Shows how many items match your keywords (e.g., "Found 847 items")

# Step 2: AI matching with Gemini
python3 ai_matching/step2_gemini.py

# Output: data/ai_matches.json
# Shows match progress and success rate

# Step 3: Save results to database
python3 ai_matching/step3_save.py

# High-confidence matches (≥90%) → Saved to matched_products table
# Medium-confidence (70-89%) → Saved to data/medium_confidence_matches_for_review.csv

# Step 4: Generate analysis report
python3 ai_matching/step4_report.py

# Output: Detailed price comparison and opportunity analysis
```

**Cost:** ~$0.02 for 1,000 items (~20 API calls × $0.001)

---

### **Step 5: View Results in Looker**

Use the `vw_matched_products_analysis` view in Looker Studio to see:
- Match scores and confidence levels
- Price comparisons (market price vs your FOB price)
- Savings opportunities (percentage difference)
- Geographic distribution of matches
- Organization types buying matched products

**Create dashboards:**
- Opportunity tracker (filter by `opportunity_level`: High/Medium/Low)
- Price comparison charts
- State-by-state analysis
- Monthly trends

---

## 🔄 Recommended Schedule

### Daily (Automated):
```bash
# Cron job or Cloud Scheduler
0 2 * * * cd /path/to/Medical && python3 main.py --start $(date -d "yesterday" +%Y%m%d) --end $(date +%Y%m%d) --states SP RJ MG
```

### Weekly (Manual):
1. Review Looker Studio dashboards
2. Identify new interesting product categories
3. Update `keywords.json` if needed
4. Run `ai_matching/` module for new categories

### Monthly (Manual):
1. Review medium-confidence matches CSV
2. Manually verify and add to database if valid
3. Update Fernandes catalog if new products added
4. Re-run matching for updated catalog

---

## 📊 Example Workflow

**Week 1:**
```bash
# Monday: Run main.py for last 7 days
python3 main.py --start 20250101 --end 20250107 --states SP

# Tuesday: Explore in Looker, find "curativos" category looks promising
# Update keywords.json: ["curativo", "bandagem", "gaze"]

# Wednesday: Run AI matching
python3 ai_matching/step1_extract_keywords.py  # Found 847 items
python3 ai_matching/step2_gemini.py            # Matched 623 items (73%)
python3 ai_matching/step3_save.py              # Saved 456 high-confidence matches

# Thursday: Review results in Looker
# View vw_matched_products_analysis
# Found 23 high-opportunity items (>30% price difference)
```

**Week 2:**
```bash
# Monday: Run main.py for last 7 days
python3 main.py --start 20250108 --end 20250114 --states SP

# No new matching needed - use same keywords.json
# Just monitor Looker dashboards for new tenders
```

---

## 🆚 When to Use Phase 3 vs AI Matching

### Use Phase 3 (--match flag):
- ✅ You want to match EVERYTHING quickly (fuzzy matching)
- ✅ You have a very large Fernandes catalog (1000+ products)
- ✅ You want fully automated workflow
- ❌ But match quality will be ~30%

```bash
python3 main.py --start 20250101 --end 20250131 --states SP --match
```

### Use AI Matching (Recommended):
- ✅ You want high-quality matches (70% success rate)
- ✅ You want to focus on specific product categories
- ✅ You're okay with a semi-manual exploration step
- ✅ Better for targeted business intelligence

```bash
# Run main.py WITHOUT --match, then run ai_matching/ separately
python3 main.py --start 20250101 --end 20250131 --states SP
# ... explore in Looker ...
python3 ai_matching/step1_extract_keywords.py
python3 ai_matching/step2_gemini.py
python3 ai_matching/step3_save.py
```

---

## 🛠️ Customization

### Add Custom Looker Views

Edit `looker_views.sql` and add your own:

```sql
CREATE OR REPLACE VIEW vw_my_custom_products AS
SELECT * FROM vw_tender_items_complete
WHERE LOWER(item_description) LIKE '%your_product%'
   OR LOWER(item_description) LIKE '%another_keyword%';
```

### Adjust AI Matching Parameters

Edit `ai_matching/step2_gemini.py`:

```python
# Line 49: Adjust batch size
self.batch_size = 30  # Smaller = more precise, slower
self.batch_size = 100 # Larger = faster, less precise
```

Edit `ai_matching/step3_save.py`:

```python
# Adjust confidence thresholds
high_confidence = [m for m in matches if m['confidence'] >= 85]  # Lower from 90
medium_confidence = [m for m in matches if 60 <= m['confidence'] < 85]  # Lower from 70
```

---

## 📈 Success Metrics

Track these in Looker Studio:

1. **Match Rate:** % of filtered items successfully matched
   - Target: >70% for AI matching
   - Baseline: ~30% for fuzzy matching

2. **Opportunity Value:** Total savings potential across all matches
   - Sum of: (market_price - your_price) × quantity

3. **Coverage:** % of tender items that match ANY filter/view
   - Shows how well your views capture relevant products

4. **Geographic Distribution:** Which states have most opportunities
   - Helps prioritize sales efforts

---

## 🚀 Next Steps

1. **Test the workflow:**
   ```bash
   # Start small
   python3 main.py --start 20250101 --end 20250107 --states SP
   # Explore in Looker
   # Run ai_matching with 2-3 keywords
   ```

2. **Set up Looker Studio:**
   - Follow `LOOKER_STUDIO_GUIDE.md`
   - Create initial dashboards
   - Share with team

3. **Automate daily runs:**
   - Set up cron job or Cloud Scheduler
   - Monitor via Looker dashboards
   - Run ai_matching weekly for new categories

4. **Iterate:**
   - Add new keywords based on discoveries
   - Refine Looker views
   - Update Fernandes catalog
   - Re-run matching as needed

---

## ❓ FAQ

**Q: Can I still use Phase 3 automatic matching?**
A: Yes! Use `--match` flag: `python3 main.py --start DATE --end DATE --match`

**Q: How much does AI matching cost?**
A: ~$0.02 per 1,000 items (~20 Gemini API calls × $0.001 each)

**Q: Can I run main.py without Looker Studio?**
A: Yes, but you'll miss the exploration step. You can still run ai_matching/ with manually chosen keywords.

**Q: What if I have 10,000 unmatched items?**
A: Use Looker views to filter first, then match specific categories. Don't try to match everything at once.

**Q: Can I match against multiple product catalogs?**
A: Yes, update `fernandes_products.json` with combined catalog, or run ai_matching/ separately for each catalog.

---

## 📞 Support

- Documentation: See `README.md` and `ai_matching/README.md`
- Looker Setup: See `LOOKER_STUDIO_GUIDE.md`
- SQL Views: See `looker_views.sql`
- Issues: Open GitHub issue

---

**V8 Branch - Optimized for Looker Studio exploration and AI-powered matching** 🚀
