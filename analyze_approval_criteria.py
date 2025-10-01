#!/usr/bin/env python3
"""
Quick analysis of what gets auto-approved in Phase 1
"""

# Examples of tenders that would be AUTO-APPROVED (Phase 1):

print("=" * 70)
print("PHASE 1: AUTO-APPROVED TENDERS (No API calls)")
print("=" * 70)

print("\n✅ HIGH CONFIDENCE EXAMPLES (score >= 70):\n")

examples_high_score = [
    {
        "org": "HOSPITAL MUNICIPAL DE SANTOS",
        "objeto": "Aquisição de material médico",
        "why": "Hospital (30pts) + material médico (25pts) = 55+ in org, 25 in object = 80 total"
    },
    {
        "org": "SECRETARIA MUNICIPAL DE SAÚDE",
        "objeto": "Pregão para medicamentos diversos",
        "why": "Saúde (25pts) + medicamentos (25pts) = 50+ total"
    },
    {
        "org": "SANTA CASA DE MISERICÓRDIA",
        "objeto": "Aquisição de equipamentos hospitalares",
        "why": "Santa Casa (25pts) + hospitalar (20pts) = 45+ total, likely 70+"
    }
]

for ex in examples_high_score:
    print(f"  Organization: {ex['org']}")
    print(f"  Object: {ex['objeto']}")
    print(f"  Why approved: {ex['why']}\n")

print("\n✅ MULTIPLE KEYWORDS EXAMPLES (2+ medical keywords):\n")

examples_keywords = [
    {
        "objeto": "Aquisição de medicamentos, equipamentos médicos e material hospitalar",
        "keywords": ["medicamentos", "médicos", "hospitalar"],
        "count": 3
    },
    {
        "objeto": "Pregão para material cirúrgico e equipamento hospitalar",
        "keywords": ["cirúrgico", "hospitalar"],
        "count": 2
    },
    {
        "objeto": "Aquisição de insumos médicos para tratamento hospitalar",
        "keywords": ["médicos", "tratamento", "hospitalar"],
        "count": 3
    },
    {
        "objeto": "Material de laboratório e medicamentos para análises",
        "keywords": ["laboratório", "medicamentos"],
        "count": 2
    }
]

for ex in examples_keywords:
    print(f"  Object: {ex['objeto']}")
    print(f"  Keywords found: {', '.join(ex['keywords'])} ({ex['count']} total)")
    print(f"  Auto-approved: YES (2+ keywords)\n")

print("\n" + "=" * 70)
print("PHASE 2: NEEDS SAMPLING (API calls required)")
print("=" * 70)

print("\n⚠️ MEDIUM CONFIDENCE EXAMPLES (40-69 score, 1 keyword):\n")

examples_needs_sampling = [
    {
        "org": "PREFEITURA MUNICIPAL DE SÃO PAULO",
        "objeto": "Aquisição de material hospitalar",
        "keywords": ["hospitalar"],
        "why": "Only 1 keyword, non-medical org name → needs verification"
    },
    {
        "org": "SECRETARIA DE ADMINISTRAÇÃO",
        "objeto": "Pregão para equipamento médico",
        "keywords": ["médico"],
        "why": "Only 1 keyword, generic org → needs item sampling"
    }
]

for ex in examples_needs_sampling:
    print(f"  Organization: {ex['org']}")
    print(f"  Object: {ex['objeto']}")
    print(f"  Keywords: {', '.join(ex['keywords'])}")
    print(f"  Why sampled: {ex['why']}\n")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("\nPhase 1 catches:")
print("  ✅ Clear medical organizations (hospitals, health secretaries)")
print("  ✅ Objects with 2+ medical keywords")
print("  ✅ High confidence combinations")
print("\nPhase 2 samples:")
print("  ⚠️  Generic organizations with 1 medical keyword")
print("  ⚠️  Medium confidence cases needing verification")
print("\nPhase 3 approves:")
print("  ✅ Tenders from organizations with proven medical history")
