/**
 * Legal Metrology (Packaged Commodities) Rules, 2011 Validation Engine
 */

function validateLegalMetrologyRules(parsedFields, fullText = '') {
  const violations = [];
  const textLower = (fullText + ' ' + JSON.stringify(parsedFields)).toLowerCase();

  // -------------------------------------------------------------
  // RULE 1: MRP Declaration & Tax Syntax Check (Rule 6(1)(e))
  // -------------------------------------------------------------
  const mrpRaw = parsedFields.mrp_raw;
  
  if (!mrpRaw) {
    violations.append ? null : violations.push({
      rule: 'Rule 6(1)(e)',
      category: 'MRP Declaration',
      severity: 'CRITICAL',
      issue: 'Maximum Retail Price (MRP) declaration is completely missing.'
    });
  } else {
    // Check for tax statement "inclusive of all taxes"
    if (!textLower.includes('incl') && !textLower.includes('tax')) {
      violations.push({
        rule: 'Rule 6(1)(e)',
        category: 'MRP Syntax',
        severity: 'MAJOR',
        found: mrpRaw,
        issue: "MRP text must explicitly state 'inclusive of all taxes'."
      });
    }
    
    // Check for misleading "Taxes Extra"
    if (textLower.includes('extra') && textLower.includes('tax')) {
      violations.push({
        rule: 'Rule 6(1)(e)',
        category: 'MRP Syntax',
        severity: 'CRITICAL',
        found: mrpRaw,
        issue: "Misleading price statement 'Taxes Extra' detected. Illegal under Legal Metrology Act 2009."
      });
    }
  }

  // -------------------------------------------------------------
  // RULE 2: Standard Units Verification for Net Qty (Rule 13)
  // -------------------------------------------------------------
  const netQtyRaw = parsedFields.net_qty_raw;
  
  if (!netQtyRaw) {
    violations.push({
      rule: 'Rule 6(1)(c)',
      category: 'Net Quantity',
      severity: 'CRITICAL',
      issue: 'Net Quantity declaration is missing.'
    });
  } else {
    // Check for non-standard unit symbols (gms, gm, kilo, ltrs, ltr)
    const invalidSymbols = ['gms', 'gm', 'kilo', 'kilos', 'ltrs', 'ltr', 'net wt'];
    for (const invalid of invalidSymbols) {
      const regex = new RegExp(`\\b${invalid}\\b`, 'i');
      if (regex.test(netQtyRaw)) {
        violations.push({
          rule: 'Rule 13',
          category: 'Standard Units',
          severity: 'MAJOR',
          found: netQtyRaw,
          issue: `Non-standard unit symbol '${invalid}' detected. Legal Metrology Rules mandate standard symbols ('g', 'kg', 'ml', 'l', 'N'). Unit symbols must never take plural 's'.`
        });
        break;
      }
    }
  }

  // -------------------------------------------------------------
  // RULE 3: Month & Year of Manufacture/Packing (Rule 6(1)(d))
  // -------------------------------------------------------------
  if (!parsedFields.mfg_date_raw) {
    violations.push({
      rule: 'Rule 6(1)(d)',
      category: 'Mfg Date',
      severity: 'MAJOR',
      issue: 'Month and Year of manufacture / packing / import is missing.'
    });
  }

  // -------------------------------------------------------------
  // RULE 4: Consumer Care Contact Details (Rule 6(1)(f))
  // -------------------------------------------------------------
  if (!parsedFields.consumer_care_email && !parsedFields.consumer_care_phone) {
    violations.push({
      rule: 'Rule 6(1)(f)',
      category: 'Consumer Care',
      severity: 'CRITICAL',
      issue: 'Consumer care contact details (Phone / Email) are missing.'
    });
  }

  // -------------------------------------------------------------
  // RULE 5: Manufacturer / Packer / Importer Details (Rule 6(1)(a))
  // -------------------------------------------------------------
  if (!parsedFields.manufacturer_details) {
    violations.push({
      rule: 'Rule 6(1)(a)',
      category: 'Manufacturer Address',
      severity: 'MAJOR',
      issue: 'Complete name and postal address of manufacturer/packer/importer is missing or incomplete.'
    });
  }

  const isCompliant = violations.length === 0;

  return {
    status: isCompliant ? 'PASS' : 'NON_COMPLIANT',
    total_violations: violations.length,
    violations: violations
  };
}

module.exports = { validateLegalMetrologyRules };
