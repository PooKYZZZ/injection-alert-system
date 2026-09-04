# Search Records follow-up results

Scope: local demo portal GET /records/search?query=... only.
All rows retain exact payloads in the JSON report.

## Summary

- Preserved SQL baseline: 50 cases.
- Preserved original Code Injection positives: 12 cases.
- New Code Injection variations: 58/100 correct (58.0%).
- Combined original 50 + new 100 Code Injection catalogue: 70/150 correct (46.67%).
- Normal traffic: 30/50 correct (60.0%); false positives=20.

## Code-expansion predicted labels

JSON values are stored in the report alongside the exact rows.
{
  "Code Injection": 58,
  "Other Attacks": 17,
  "SQL Injection": 25
}

## Code-expansion mutation summary

| Mutation | Tested | Correct | Accuracy |
| --- | ---: | ---: | ---: |
| alternate_delimiter_variation | 12 | 6 | 50.0% |
| argument_form_variation | 4 | 3 | 75.0% |
| case_variation | 12 | 8 | 66.67% |
| comment_variation | 12 | 1 | 8.33% |
| encoded_spacing_variation | 12 | 12 | 100.0% |
| quoted_argument_variation | 12 | 4 | 33.33% |
| separator_variation | 12 | 11 | 91.67% |
| whitespace_expansion | 12 | 8 | 66.67% |
| wrapper_variation | 12 | 5 | 41.67% |

## Misclassified Code Injection cases

| Case | Seed | Mutation | Exact payload | Predicted | Confidence | Tier | Correct |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| SR-CODE-EXP-003 | SR-CODE-021 | wrapper_variation | (__import__('math').sqrt(4)) # CYBERTRACE_EXP_003 | SQL Injection | 0.998900 | CRITICAL | False |
| SR-CODE-EXP-007 | SR-CODE-021 | comment_variation | __import__('math').sqrt(4) # CYBERTRACE_EXP_007 | SQL Injection | 0.999057 | CRITICAL | False |
| SR-CODE-EXP-019 | SR-CODE-023 | whitespace_expansion | __IMPORT__('MATH').SQRT(4)  | SQL Injection | 0.998407 | CRITICAL | False |
| SR-CODE-EXP-020 | SR-CODE-023 | case_variation | __import__('math').sqrt(4) /*CYBERTRACE_EXP_020*/ | SQL Injection | 0.989445 | CRITICAL | False |
| SR-CODE-EXP-022 | SR-CODE-023 | quoted_argument_variation | __IMPORT__('MATH').SQRT(4) + 0 | SQL Injection | 0.998926 | CRITICAL | False |
| SR-CODE-EXP-025 | SR-CODE-023 | comment_variation | __IMPORT__('MATH').SQRT(4) /*CYBERTRACE_EXP_025*/ | SQL Injection | 0.989765 | CRITICAL | False |
| SR-CODE-EXP-027 | SR-CODE-023 | argument_form_variation | __IMPORT__('MATH').SQRT(4) + (0) | SQL Injection | 0.998106 | CRITICAL | False |
| SR-CODE-EXP-028 | SR-CODE-024 | whitespace_expansion |  (__import__('math').sqrt(4)) | SQL Injection | 0.981959 | CRITICAL | False |
| SR-CODE-EXP-034 | SR-CODE-024 | comment_variation | (__import__('math').sqrt(4)) # CYBERTRACE_EXP_034 | SQL Injection | 0.998818 | CRITICAL | False |
| SR-CODE-EXP-039 | SR-CODE-032 | wrapper_variation | ( function(){return${IFS}1} ) | SQL Injection | 0.833308 | HIGH | False |
| SR-CODE-EXP-040 | SR-CODE-032 | quoted_argument_variation | function(){return${IFS}1} 'CYBERTRACE_TEST' | SQL Injection | 0.669313 | MEDIUM | False |
| SR-CODE-EXP-042 | SR-CODE-032 | alternate_delimiter_variation | function(){return${IFS}1} && printf CYBERTRACE_TEST | SQL Injection | 0.988311 | CRITICAL | False |
| SR-CODE-EXP-043 | SR-CODE-032 | comment_variation | function(){return${IFS}1} # CYBERTRACE_EXP_043 | SQL Injection | 0.783643 | MEDIUM | False |
| SR-CODE-EXP-045 | SR-CODE-034 | whitespace_expansion | (function(){return  1}) | Other Attacks | 0.539551 | MEDIUM | False |
| SR-CODE-EXP-049 | SR-CODE-034 | separator_variation | (function(){return 1}); 2 + 2 | SQL Injection | 0.989793 | CRITICAL | False |
| SR-CODE-EXP-051 | SR-CODE-034 | comment_variation | (function(){return 1}) // CYBERTRACE_EXP_051 | SQL Injection | 0.988891 | CRITICAL | False |
| SR-CODE-EXP-055 | SR-CODE-035 | wrapper_variation | ( function(){ret${IFS}urn 1} ) | SQL Injection | 0.795968 | MEDIUM | False |
| SR-CODE-EXP-056 | SR-CODE-035 | quoted_argument_variation | function(){ret${IFS}urn 1} 'CYBERTRACE_TEST' | Other Attacks | 0.645098 | MEDIUM | False |
| SR-CODE-EXP-058 | SR-CODE-035 | alternate_delimiter_variation | function(){ret${IFS}urn 1} && printf CYBERTRACE_TEST | SQL Injection | 0.991985 | CRITICAL | False |
| SR-CODE-EXP-059 | SR-CODE-035 | comment_variation | function(){ret${IFS}urn 1} # CYBERTRACE_EXP_059 | SQL Injection | 0.796456 | MEDIUM | False |
| SR-CODE-EXP-062 | SR-CODE-036 | case_variation | ${7*7} # CYBERTRACE_EXP_062 | Other Attacks | 0.803049 | HIGH | False |
| SR-CODE-EXP-063 | SR-CODE-036 | wrapper_variation | ( ${7*7} ) | Other Attacks | 0.662945 | MEDIUM | False |
| SR-CODE-EXP-064 | SR-CODE-036 | quoted_argument_variation | ${7*7} 'CYBERTRACE_TEST' | Other Attacks | 0.952558 | CRITICAL | False |
| SR-CODE-EXP-066 | SR-CODE-036 | alternate_delimiter_variation | ${7*7} && printf CYBERTRACE_TEST | SQL Injection | 0.989464 | CRITICAL | False |
| SR-CODE-EXP-067 | SR-CODE-036 | comment_variation | ${7*7} # CYBERTRACE_EXP_067 | Other Attacks | 0.816754 | HIGH | False |
| SR-CODE-EXP-071 | SR-CODE-037 | wrapper_variation | ( ${7*7};echo ) | Other Attacks | 0.990326 | CRITICAL | False |
| SR-CODE-EXP-072 | SR-CODE-037 | quoted_argument_variation | ${7*7};echo 'CYBERTRACE_TEST' | Other Attacks | 0.989793 | CRITICAL | False |
| SR-CODE-EXP-074 | SR-CODE-037 | alternate_delimiter_variation | ${7*7};echo && printf CYBERTRACE_TEST | Other Attacks | 0.862200 | HIGH | False |
| SR-CODE-EXP-075 | SR-CODE-037 | comment_variation | ${7*7};echo # CYBERTRACE_EXP_075 | Other Attacks | 0.870572 | HIGH | False |
| SR-CODE-EXP-078 | SR-CODE-039 | case_variation | (${7*7}) # CYBERTRACE_EXP_078 | Other Attacks | 0.585891 | MEDIUM | False |
| SR-CODE-EXP-079 | SR-CODE-039 | wrapper_variation | ( (${7*7}) ) | SQL Injection | 0.904364 | CRITICAL | False |
| SR-CODE-EXP-080 | SR-CODE-039 | quoted_argument_variation | (${7*7}) 'CYBERTRACE_TEST' | Other Attacks | 0.947946 | CRITICAL | False |
| SR-CODE-EXP-082 | SR-CODE-039 | alternate_delimiter_variation | (${7*7}) && printf CYBERTRACE_TEST | SQL Injection | 0.996235 | CRITICAL | False |
| SR-CODE-EXP-083 | SR-CODE-039 | comment_variation | (${7*7}) # CYBERTRACE_EXP_083 | Other Attacks | 0.536940 | MEDIUM | False |
| SR-CODE-EXP-085 | SR-CODE-044 | whitespace_expansion | (#{7 * 7}) | SQL Injection | 0.598316 | MEDIUM | False |
| SR-CODE-EXP-086 | SR-CODE-044 | case_variation | (#{7*7}) /*CYBERTRACE_EXP_086*/ | SQL Injection | 0.977275 | CRITICAL | False |
| SR-CODE-EXP-088 | SR-CODE-044 | quoted_argument_variation | (#{7*7}) + 0 | SQL Injection | 0.983133 | CRITICAL | False |
| SR-CODE-EXP-091 | SR-CODE-044 | comment_variation | (#{7*7}) /*CYBERTRACE_EXP_091*/ | SQL Injection | 0.982904 | CRITICAL | False |
| SR-CODE-EXP-095 | SR-CODE-047 | wrapper_variation | ( {{7*7}};echo ) | Other Attacks | 0.984597 | CRITICAL | False |
| SR-CODE-EXP-096 | SR-CODE-047 | quoted_argument_variation | {{7*7}};echo 'CYBERTRACE_TEST' | Other Attacks | 0.979407 | CRITICAL | False |
| SR-CODE-EXP-098 | SR-CODE-047 | alternate_delimiter_variation | {{7*7}};echo && printf CYBERTRACE_TEST | Other Attacks | 0.864502 | HIGH | False |
| SR-CODE-EXP-099 | SR-CODE-047 | comment_variation | {{7*7}};echo # CYBERTRACE_EXP_099 | Other Attacks | 0.957153 | CRITICAL | False |

## Known normal traffic

| Case | Exact query | Predicted | Confidence | Tier | Correct |
| --- | --- | --- | ---: | --- | --- |
| SR-NORMAL-001 | LND-2026-0001 | Normal | 0.749985 | MEDIUM | True |
| SR-NORMAL-002 | LND-2026-0002 | Normal | 0.738394 | MEDIUM | True |
| SR-NORMAL-003 | LND-2026-0003 | Normal | 0.754275 | MEDIUM | True |
| SR-NORMAL-004 | LND-2026-0004 | Normal | 0.770515 | MEDIUM | True |
| SR-NORMAL-005 | LND-2026-0005 | Normal | 0.765544 | MEDIUM | True |
| SR-NORMAL-006 | LND-2026-0006 | Normal | 0.766274 | MEDIUM | True |
| SR-NORMAL-007 | LND-2026-0007 | Normal | 0.769619 | MEDIUM | True |
| SR-NORMAL-008 | LND-2026-0008 | Normal | 0.776783 | MEDIUM | True |
| SR-NORMAL-009 | LND-2026-0009 | Normal | 0.760861 | MEDIUM | True |
| SR-NORMAL-010 | LND-2026-0010 | Normal | 0.745054 | MEDIUM | True |
| SR-NORMAL-019 | North District | Normal | 0.605229 | MEDIUM | True |
| SR-NORMAL-020 | North Branch | Normal | 0.544891 | MEDIUM | True |
| SR-NORMAL-021 | Crest Branch | Normal | 0.570682 | MEDIUM | True |
| SR-NORMAL-022 | South Branch | Normal | 0.660515 | MEDIUM | True |
| SR-NORMAL-023 | Registry Sector | Normal | 0.603208 | MEDIUM | True |
| SR-NORMAL-027 | Commercial | Normal | 0.659948 | MEDIUM | True |
| SR-NORMAL-029 | Mixed Use | Normal | 0.528972 | MEDIUM | True |
| SR-NORMAL-030 | Historical Preserve | Normal | 0.647797 | MEDIUM | True |
| SR-NORMAL-033 | Title Deed Transfer | Normal | 0.776880 | MEDIUM | True |
| SR-NORMAL-034 | Active Registered | Normal | 0.696057 | MEDIUM | True |
| SR-NORMAL-035 | Collateralized | Normal | 0.531638 | MEDIUM | True |
| SR-NORMAL-038 | Property title | Normal | 0.750366 | MEDIUM | True |
| SR-NORMAL-039 | Record lookup | Normal | 0.597891 | MEDIUM | True |
| SR-NORMAL-041 | Survey date | Normal | 0.620521 | MEDIUM | True |
| SR-NORMAL-042 | Owner name | Normal | 0.668428 | MEDIUM | True |
| SR-NORMAL-043 | Record number | Normal | 0.523758 | MEDIUM | True |
| SR-NORMAL-044 | North District registry | Normal | 0.620291 | MEDIUM | True |
| SR-NORMAL-046 | Commercial property | Normal | 0.721215 | MEDIUM | True |
| SR-NORMAL-049 | Deed transfer processing | Normal | 0.484096 | LOW | True |
| SR-NORMAL-050 | Sample cadastral index | Normal | 0.668330 | MEDIUM | True |

## Normal false positives

| Case | Exact query | Predicted | Confidence | Tier |
| --- | --- | --- | ---: | --- |
| SR-NORMAL-011 | Maria Santos | Other Attacks | 0.926761 | CRITICAL |
| SR-NORMAL-012 | Daniel Reyes | Other Attacks | 0.755211 | MEDIUM |
| SR-NORMAL-013 | Elena Cruz | Other Attacks | 0.861504 | HIGH |
| SR-NORMAL-014 | Ramon Garcia | Other Attacks | 0.680337 | MEDIUM |
| SR-NORMAL-015 | Maria | Other Attacks | 0.918005 | CRITICAL |
| SR-NORMAL-016 | Daniel | Other Attacks | 0.661789 | MEDIUM |
| SR-NORMAL-017 | Elena | Other Attacks | 0.918340 | CRITICAL |
| SR-NORMAL-018 | Ramon | Other Attacks | 0.741835 | MEDIUM |
| SR-NORMAL-024 | Malibu Point | Other Attacks | 0.649689 | MEDIUM |
| SR-NORMAL-025 | Mountain Drive | Other Attacks | 0.972186 | CRITICAL |
| SR-NORMAL-026 | Residential | Other Attacks | 0.640421 | MEDIUM |
| SR-NORMAL-028 | Agricultural | Other Attacks | 0.844002 | HIGH |
| SR-NORMAL-031 | Cultivation Yard | Other Attacks | 0.760445 | MEDIUM |
| SR-NORMAL-032 | Property Partitioning | Other Attacks | 0.675284 | MEDIUM |
| SR-NORMAL-036 | Public land records | Other Attacks | 0.927750 | CRITICAL |
| SR-NORMAL-037 | Search land records | Other Attacks | 0.951473 | CRITICAL |
| SR-NORMAL-040 | Parcel boundary | Other Attacks | 0.549617 | MEDIUM |
| SR-NORMAL-045 | Residential property | Other Attacks | 0.770096 | MEDIUM |
| SR-NORMAL-047 | Agricultural land | Other Attacks | 0.918901 | CRITICAL |
| SR-NORMAL-048 | Certified copy | Other Attacks | 0.691587 | MEDIUM |
