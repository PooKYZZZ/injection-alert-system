# Search Records Code Injection Expansion Round 2

Scope: local `GET /records/search?query=...` only; payloads were not executed.

## Summary

- Preserved classifier-positive seeds: 70.
- New variations tested: 200.
- New Code Injection matches: 78 (39.0%).
- New misclassifications: 122.
- Seed-plus-new confirmed total: 148 of 270 (54.81%).
- Correlation: 200/200 requests executed, 200 audit-correlated, 200 bridge-correlated, 200 terminal predictions.

## Predicted labels

```json
{
  "Code Injection": 78,
  "Other Attacks": 15,
  "SQL Injection": 107
}
```

## Confidence levels

```json
{
  "CRITICAL": 108,
  "HIGH": 23,
  "LOW": 7,
  "MEDIUM": 62
}
```

## Mutation results

| Mutation | Tested | Correct | Accuracy |
| --- | ---: | ---: | ---: |
| alternate_delimiter | 14 | 1 | 7.14% |
| argument_rewrite | 14 | 6 | 42.86% |
| block_wrapper | 14 | 2 | 14.29% |
| case_marker_context | 14 | 6 | 42.86% |
| comment_boundary | 14 | 1 | 7.14% |
| computed_call_wrapper | 15 | 10 | 66.67% |
| encoded_delimiter_chain | 15 | 9 | 60.0% |
| encoded_wrapper_chain | 14 | 13 | 92.86% |
| line_break_boundary | 14 | 9 | 64.29% |
| nested_block_context | 15 | 1 | 6.67% |
| nested_expression | 14 | 2 | 14.29% |
| operator_chain | 14 | 0 | 0.0% |
| quote_form_rewrite | 14 | 8 | 57.14% |
| separator_expression | 15 | 10 | 66.67% |

## Misclassified round-two cases

| Case | Seed | Mutation | Full payload | Predicted | Confidence | Tier |
| --- | --- | --- | --- | --- | ---: | --- |
| SR-CODE-R2-002 | SR-CODE-021 | block_wrapper | (lambda: (__import__('math').sqrt(4)))(); (4-1) | SQL Injection | 0.661233 | MEDIUM |
| SR-CODE-R2-006 | SR-CODE-022 | encoded_delimiter_chain | __import__%28'math'%29.sqrt%284%29%3Becho%0A8%2B0 | SQL Injection | 0.930479 | CRITICAL |
| SR-CODE-R2-007 | SR-CODE-023 | comment_boundary | __IMPORT__('MATH').SQRT(4) # CYBERTRACE_R2_007
(2-1) | SQL Injection | 0.997505 | CRITICAL |
| SR-CODE-R2-010 | SR-CODE-024 | alternate_delimiter | [(__import__('math').sqrt(4)), 5-5] | SQL Injection | 0.991788 | CRITICAL |
| SR-CODE-R2-012 | SR-CODE-024 | nested_block_context | (
  ((__import__('math').sqrt(4)))
)
+ 7-0 | SQL Injection | 0.999030 | CRITICAL |
| SR-CODE-R2-013 | SR-CODE-032 | operator_chain | function(){return${IFS}1} && printf '%s' CYBERTRACE_TEST || printf '%s' CYBERTRACE_TEST | SQL Injection | 0.999001 | CRITICAL |
| SR-CODE-R2-015 | SR-CODE-032 | nested_expression | ( function(){return${IFS}1}; printf '%s' CYBERTRACE_TEST ) | SQL Injection | 0.941864 | CRITICAL |
| SR-CODE-R2-016 | SR-CODE-034 | block_wrapper | function CYBERTRACE_R2_016(){return ((function(){return 1}));} | SQL Injection | 0.780901 | MEDIUM |
| SR-CODE-R2-018 | SR-CODE-034 | line_break_boundary | {
  (function(){return 1})
}
(6+0) | SQL Injection | 0.994152 | CRITICAL |
| SR-CODE-R2-019 | SR-CODE-035 | quote_form_rewrite | printf "%s" CYBERTRACE_TEST; function(){ret${IFS}urn 1} | SQL Injection | 0.899479 | HIGH |
| SR-CODE-R2-021 | SR-CODE-035 | comment_boundary | function(){ret${IFS}urn 1} # CYBERTRACE_R2_021
printf '%s' CYBERTRACE_TEST | SQL Injection | 0.997263 | CRITICAL |
| SR-CODE-R2-022 | SR-CODE-036 | argument_rewrite | {{ (3+3) }}; ${7*7} | SQL Injection | 0.983517 | CRITICAL |
| SR-CODE-R2-024 | SR-CODE-036 | alternate_delimiter | [{{ ${7*7} }}] | Other Attacks | 0.718766 | MEDIUM |
| SR-CODE-R2-025 | SR-CODE-037 | case_marker_context | CYBERTRACEFLAG025=6; ${7*7};echo | Other Attacks | 0.973803 | CRITICAL |
| SR-CODE-R2-026 | SR-CODE-037 | nested_block_context | { { ${7*7};echo; }; } | Other Attacks | 0.842401 | HIGH |
| SR-CODE-R2-027 | SR-CODE-037 | operator_chain | ${7*7};echo && printf '%s' CYBERTRACE_TEST || printf '%s' CYBERTRACE_TEST | SQL Injection | 0.996821 | CRITICAL |
| SR-CODE-R2-029 | SR-CODE-039 | nested_expression | {{ ((${7*7})) + (3*1) }} | SQL Injection | 0.995784 | CRITICAL |
| SR-CODE-R2-033 | SR-CODE-044 | quote_form_rewrite | {{ "CYBERTRACE_TEST" }}; (#{7*7}) | SQL Injection | 0.470511 | LOW |
| SR-CODE-R2-035 | SR-CODE-047 | comment_boundary | {{7*7}};echo # CYBERTRACE_R2_035
printf '%s' CYBERTRACE_TEST | SQL Injection | 0.629340 | MEDIUM |
| SR-CODE-R2-036 | SR-CODE-047 | argument_rewrite | $(printf '%s' CYBERTRACE_TEST); {{7*7}};echo | SQL Injection | 0.590959 | MEDIUM |
| SR-CODE-R2-038 | SR-CODE-EXP-001 | alternate_delimiter | [__import__ ('math').sqrt(4), 5-5] | SQL Injection | 0.974540 | CRITICAL |
| SR-CODE-R2-040 | SR-CODE-EXP-002 | nested_block_context | (
  (__IMPORT__('math').sqrt(4))
)
+ 7-0 | SQL Injection | 0.999176 | CRITICAL |
| SR-CODE-R2-041 | SR-CODE-EXP-002 | operator_chain | (__IMPORT__('math').sqrt(4)) or (8 == 8) | SQL Injection | 0.999251 | CRITICAL |
| SR-CODE-R2-044 | SR-CODE-EXP-004 | block_wrapper | (lambda: (__import__("math").sqrt(4)))(); (4-1) | SQL Injection | 0.577210 | MEDIUM |
| SR-CODE-R2-048 | SR-CODE-EXP-005 | encoded_delimiter_chain | __import__%28'math'%29.sqrt%284%29%3B%202+2%0A8%2B0 | SQL Injection | 0.995835 | CRITICAL |
| SR-CODE-R2-049 | SR-CODE-EXP-006 | comment_boundary | [__import__('math').sqrt(4)] # CYBERTRACE_R2_049
(2-1) | SQL Injection | 0.995742 | CRITICAL |
| SR-CODE-R2-052 | SR-CODE-EXP-008 | alternate_delimiter | [__import__('math').sqrt(4)%0a, 5-5] | SQL Injection | 0.591328 | MEDIUM |
| SR-CODE-R2-053 | SR-CODE-EXP-008 | case_marker_context | __import__('math').sqrt(4)%0a; cybertraceflag053 = 6 | SQL Injection | 0.514716 | MEDIUM |
| SR-CODE-R2-054 | SR-CODE-EXP-008 | nested_block_context | (
  (__import__('math').sqrt(4)%0a)
)
+ 7-0 | SQL Injection | 0.999178 | CRITICAL |
| SR-CODE-R2-055 | SR-CODE-EXP-009 | operator_chain | (__import__('math').sqrt(2+2)) or (8 == 8) | SQL Injection | 0.999406 | CRITICAL |
| SR-CODE-R2-056 | SR-CODE-EXP-009 | encoded_wrapper_chain | %28__import__('math').sqrt(2+2)%29%3B2%2B0 | SQL Injection | 0.714167 | MEDIUM |
| SR-CODE-R2-057 | SR-CODE-EXP-009 | nested_expression | ((__import__('math').sqrt(2+2))); (3-1) | SQL Injection | 0.965040 | CRITICAL |
| SR-CODE-R2-058 | SR-CODE-EXP-010 | block_wrapper | (lambda: (__import__('math').sqrt(4);echo${IFS}))(); (4-1) | SQL Injection | 0.642537 | MEDIUM |
| SR-CODE-R2-062 | SR-CODE-EXP-011 | encoded_delimiter_chain | __import__%28'math'%29.sqrt%284%29%3BECHO%0A8%2B0 | SQL Injection | 0.930479 | CRITICAL |
| SR-CODE-R2-064 | SR-CODE-EXP-012 | argument_rewrite | getattr(__import__("math"), "sqrt")(3+3); ( __import__('math').sqrt(4);echo ) | SQL Injection | 0.674331 | MEDIUM |
| SR-CODE-R2-066 | SR-CODE-EXP-012 | alternate_delimiter | [( __import__('math').sqrt(4);echo ), 5-5] | SQL Injection | 0.996783 | CRITICAL |
| SR-CODE-R2-068 | SR-CODE-EXP-013 | nested_block_context | (
  (__import__('math').sqrt(4);echo 'CYBERTRACE_TEST')
)
+ 7-0 | SQL Injection | 0.998993 | CRITICAL |
| SR-CODE-R2-069 | SR-CODE-EXP-013 | operator_chain | (__import__('math').sqrt(4);echo 'CYBERTRACE_TEST') or (8 == 8) | SQL Injection | 0.999436 | CRITICAL |
| SR-CODE-R2-071 | SR-CODE-EXP-014 | nested_expression | ((__import__('math').sqrt(4);echo; printf CYBERTRACE_TEST)); (3-1) | SQL Injection | 0.709048 | MEDIUM |
| SR-CODE-R2-072 | SR-CODE-EXP-014 | block_wrapper | (lambda: (__import__('math').sqrt(4);echo; printf CYBERTRACE_TEST))(); (4-1) | SQL Injection | 0.881585 | HIGH |
| SR-CODE-R2-073 | SR-CODE-EXP-015 | separator_expression | __import__('math').sqrt(4);echo && printf CYBERTRACE_TEST; (5-1) | SQL Injection | 0.810419 | HIGH |
| SR-CODE-R2-076 | SR-CODE-EXP-016 | encoded_delimiter_chain | __import__%28'math'%29.sqrt%284%29%3Becho%20#%20CYBERTRACE_EXP_016%0A8%2B0 | SQL Injection | 0.756780 | MEDIUM |
| SR-CODE-R2-077 | SR-CODE-EXP-016 | comment_boundary | __import__('math').sqrt(4);echo # CYBERTRACE_EXP_016 # CYBERTRACE_R2_077
(2-1) | SQL Injection | 0.979299 | CRITICAL |
| SR-CODE-R2-082 | SR-CODE-EXP-018 | nested_block_context | (
  (__import__('math').sqrt(2+2);echo)
)
+ 7-0 | SQL Injection | 0.999132 | CRITICAL |
| SR-CODE-R2-083 | SR-CODE-EXP-018 | operator_chain | (__import__('math').sqrt(2+2);echo) or (8 == 8) | SQL Injection | 0.999431 | CRITICAL |
| SR-CODE-R2-085 | SR-CODE-EXP-021 | nested_expression | (((__IMPORT__('MATH').SQRT(4)))); (3-1) | SQL Injection | 0.691572 | MEDIUM |
| SR-CODE-R2-086 | SR-CODE-EXP-021 | block_wrapper | (lambda: ((__IMPORT__('MATH').SQRT(4))))(); (4-1) | SQL Injection | 0.657506 | MEDIUM |
| SR-CODE-R2-090 | SR-CODE-EXP-023 | encoded_delimiter_chain | __IMPORT__%28'MATH'%29.SQRT%284%29%3B%202+2%0A8%2B0 | SQL Injection | 0.995835 | CRITICAL |
| SR-CODE-R2-091 | SR-CODE-EXP-024 | comment_boundary | [__IMPORT__('MATH').SQRT(4)] # CYBERTRACE_R2_091
(2-1) | SQL Injection | 0.996249 | CRITICAL |
| SR-CODE-R2-094 | SR-CODE-EXP-026 | alternate_delimiter | [__IMPORT__('MATH').SQRT(4)%0a, 5-5] | SQL Injection | 0.591328 | MEDIUM |
| SR-CODE-R2-095 | SR-CODE-EXP-026 | case_marker_context | __IMPORT__('MATH').SQRT(4)%0a; cybertraceflag095 = 6 | SQL Injection | 0.666573 | MEDIUM |
| SR-CODE-R2-096 | SR-CODE-EXP-026 | nested_block_context | (
  (__IMPORT__('MATH').SQRT(4)%0a)
)
+ 7-0 | SQL Injection | 0.999178 | CRITICAL |
| SR-CODE-R2-097 | SR-CODE-EXP-029 | operator_chain | ((__IMPORT__('math').sqrt(4))) or (8 == 8) | SQL Injection | 0.999346 | CRITICAL |
| SR-CODE-R2-099 | SR-CODE-EXP-029 | nested_expression | (((__IMPORT__('math').sqrt(4)))); (3-1) | SQL Injection | 0.691572 | MEDIUM |
| SR-CODE-R2-100 | SR-CODE-EXP-030 | block_wrapper | (lambda: (((__import__('math').sqrt(4)))))(); (4-1) | SQL Injection | 0.717124 | MEDIUM |
| SR-CODE-R2-104 | SR-CODE-EXP-031 | encoded_delimiter_chain | %28__import__%28"math"%29.sqrt%284%29%29%0A8%2B0 | SQL Injection | 0.696648 | MEDIUM |
| SR-CODE-R2-105 | SR-CODE-EXP-031 | comment_boundary | (__import__("math").sqrt(4)) # CYBERTRACE_R2_105
(2-1) | SQL Injection | 0.996589 | CRITICAL |
| SR-CODE-R2-106 | SR-CODE-EXP-032 | argument_rewrite | getattr(__import__("math"), "sqrt")(3+3); (__import__('math').sqrt(4)); 2+2 | SQL Injection | 0.660793 | MEDIUM |
| SR-CODE-R2-107 | SR-CODE-EXP-032 | computed_call_wrapper | getattr(__import__('math'), 'sqrt')(4); ((__import__('math').sqrt(4)); 2+2) | SQL Injection | 0.575275 | MEDIUM |
| SR-CODE-R2-108 | SR-CODE-EXP-032 | alternate_delimiter | [(__import__('math').sqrt(4)); 2+2, 5-5] | SQL Injection | 0.996515 | CRITICAL |
| SR-CODE-R2-109 | SR-CODE-EXP-033 | case_marker_context | [(__import__('math').sqrt(4))]; cybertraceflag109 = 6 | SQL Injection | 0.912452 | CRITICAL |
| SR-CODE-R2-110 | SR-CODE-EXP-033 | nested_block_context | (
  ([(__import__('math').sqrt(4))])
)
+ 7-0 | SQL Injection | 0.998797 | CRITICAL |
| SR-CODE-R2-111 | SR-CODE-EXP-033 | operator_chain | ([(__import__('math').sqrt(4))]) or (8 == 8) | SQL Injection | 0.999366 | CRITICAL |
| SR-CODE-R2-113 | SR-CODE-EXP-035 | nested_expression | (((__import__('math').sqrt(4))%0a)); (3-1) | SQL Injection | 0.902144 | CRITICAL |
| SR-CODE-R2-114 | SR-CODE-EXP-035 | block_wrapper | (lambda: ((__import__('math').sqrt(4))%0a))(); (4-1) | SQL Injection | 0.857679 | HIGH |
| SR-CODE-R2-115 | SR-CODE-EXP-036 | separator_expression | (__import__('math').sqrt(2+2)); (5-1) | SQL Injection | 0.639367 | MEDIUM |
| SR-CODE-R2-119 | SR-CODE-EXP-037 | comment_boundary | function(){return${IFS}1}${IFS} # CYBERTRACE_R2_119
printf '%s' CYBERTRACE_TEST | SQL Injection | 0.998434 | CRITICAL |
| SR-CODE-R2-121 | SR-CODE-EXP-038 | computed_call_wrapper | { printf '%s' CYBERTRACE_TEST; }; function(){return${ifs}1} | SQL Injection | 0.493374 | LOW |
| SR-CODE-R2-122 | SR-CODE-EXP-038 | alternate_delimiter | [ function(){return${ifs}1} ]; printf '%s' CYBERTRACE_TEST | SQL Injection | 0.991268 | CRITICAL |
| SR-CODE-R2-124 | SR-CODE-EXP-041 | nested_block_context | { { function(){return${IFS}1}; printf CYBERTRACE_TEST; }; } | Other Attacks | 0.597271 | MEDIUM |
| SR-CODE-R2-125 | SR-CODE-EXP-041 | operator_chain | function(){return${IFS}1}; printf CYBERTRACE_TEST && printf '%s' CYBERTRACE_TEST || printf '%s' CYBERTRACE_TEST | SQL Injection | 0.998226 | CRITICAL |
| SR-CODE-R2-127 | SR-CODE-EXP-044 | nested_expression | ( function(){return${IFS}1}%09; printf '%s' CYBERTRACE_TEST ) | SQL Injection | 0.967757 | CRITICAL |
| SR-CODE-R2-128 | SR-CODE-EXP-044 | block_wrapper | function CYBERTRACE_R2_128(){ printf '%s' CYBERTRACE_TEST; }; function(){return${IFS}1}%09 | SQL Injection | 0.803914 | HIGH |
| SR-CODE-R2-129 | SR-CODE-EXP-044 | separator_expression | function(){return${IFS}1}%09; printf '%s' CYBERTRACE_TEST | SQL Injection | 0.883171 | HIGH |
| SR-CODE-R2-130 | SR-CODE-EXP-046 | line_break_boundary | {
  (FUNCTION(){return 1})
}
(6+0) | SQL Injection | 0.994152 | CRITICAL |
| SR-CODE-R2-133 | SR-CODE-EXP-047 | comment_boundary | (((function(){return 1}))) // CYBERTRACE_R2_133
(2+0) | SQL Injection | 0.996992 | CRITICAL |
| SR-CODE-R2-134 | SR-CODE-EXP-047 | argument_rewrite | (()=>{const value=3+3; return value;})(); (((function(){return 1}))) | SQL Injection | 0.625785 | MEDIUM |
| SR-CODE-R2-136 | SR-CODE-EXP-048 | alternate_delimiter | [(function(){return 'CYBERTRACE_TEST'}), 5-5].map(x=>x) | SQL Injection | 0.642337 | MEDIUM |
| SR-CODE-R2-139 | SR-CODE-EXP-050 | operator_chain | ([(function(){return 1})]) || (8 === 8) | SQL Injection | 0.997431 | CRITICAL |
| SR-CODE-R2-141 | SR-CODE-EXP-050 | nested_expression | (()=>{return ([(function(){return 1})]);})(); (3+0) | SQL Injection | 0.624483 | MEDIUM |
| SR-CODE-R2-142 | SR-CODE-EXP-052 | block_wrapper | function CYBERTRACE_R2_142(){return ((function(){return%201}));} | SQL Injection | 0.672970 | MEDIUM |
| SR-CODE-R2-144 | SR-CODE-EXP-052 | line_break_boundary | {
  (function(){return%201})
}
(6+0) | SQL Injection | 0.992573 | CRITICAL |
| SR-CODE-R2-145 | SR-CODE-EXP-053 | quote_form_rewrite | printf "%s" CYBERTRACE_TEST; function(){ret${IFS}urn${IFS}1} | SQL Injection | 0.869684 | HIGH |
| SR-CODE-R2-147 | SR-CODE-EXP-053 | comment_boundary | function(){ret${IFS}urn${IFS}1} # CYBERTRACE_R2_147
printf '%s' CYBERTRACE_TEST | SQL Injection | 0.998534 | CRITICAL |
| SR-CODE-R2-149 | SR-CODE-EXP-054 | computed_call_wrapper | { printf '%s' CYBERTRACE_TEST; }; function(){ret${ifs}urn 1} | SQL Injection | 0.632913 | MEDIUM |
| SR-CODE-R2-150 | SR-CODE-EXP-054 | alternate_delimiter | [ function(){ret${ifs}urn 1} ]; printf '%s' CYBERTRACE_TEST | SQL Injection | 0.989951 | CRITICAL |
| SR-CODE-R2-151 | SR-CODE-EXP-057 | case_marker_context | CYBERTRACEFLAG151=6; function(){ret${IFS}urn 1}; printf CYBERTRACE_TEST | Other Attacks | 0.708264 | MEDIUM |
| SR-CODE-R2-152 | SR-CODE-EXP-057 | nested_block_context | { { function(){ret${IFS}urn 1}; printf CYBERTRACE_TEST; }; } | Other Attacks | 0.620752 | MEDIUM |
| SR-CODE-R2-153 | SR-CODE-EXP-057 | operator_chain | function(){ret${IFS}urn 1}; printf CYBERTRACE_TEST && printf '%s' CYBERTRACE_TEST || printf '%s' CYBERTRACE_TEST | SQL Injection | 0.998916 | CRITICAL |
| SR-CODE-R2-155 | SR-CODE-EXP-060 | nested_expression | ( function(){ret${IFS}urn%201}; printf '%s' CYBERTRACE_TEST ) | SQL Injection | 0.842258 | HIGH |
| SR-CODE-R2-156 | SR-CODE-EXP-060 | block_wrapper | function CYBERTRACE_R2_156(){ printf '%s' CYBERTRACE_TEST; }; function(){ret${IFS}urn%201} | SQL Injection | 0.613652 | MEDIUM |
| SR-CODE-R2-157 | SR-CODE-EXP-061 | separator_expression | ${7*7}${IFS}; printf '%s' CYBERTRACE_TEST | SQL Injection | 0.504247 | MEDIUM |
| SR-CODE-R2-158 | SR-CODE-EXP-061 | line_break_boundary | ${7*7}${IFS}
printf '%s' CYBERTRACE_TEST | SQL Injection | 0.708764 | MEDIUM |
| SR-CODE-R2-159 | SR-CODE-EXP-061 | quote_form_rewrite | printf "%s" CYBERTRACE_TEST; ${7*7}${IFS} | SQL Injection | 0.942630 | CRITICAL |
| SR-CODE-R2-161 | SR-CODE-EXP-065 | comment_boundary | ${7*7}; printf CYBERTRACE_TEST # CYBERTRACE_R2_161
printf '%s' CYBERTRACE_TEST | SQL Injection | 0.971608 | CRITICAL |
| SR-CODE-R2-162 | SR-CODE-EXP-065 | argument_rewrite | $(printf '%s' CYBERTRACE_TEST); ${7*7}; printf CYBERTRACE_TEST | SQL Injection | 0.939166 | CRITICAL |
| SR-CODE-R2-164 | SR-CODE-EXP-068 | alternate_delimiter | [{{ ${7*7}%09 }}] | Other Attacks | 0.577478 | MEDIUM |
| SR-CODE-R2-165 | SR-CODE-EXP-068 | case_marker_context | {{ cYBERtRACEfLAG165|${7*7}%09 }} | Other Attacks | 0.592628 | MEDIUM |
| SR-CODE-R2-166 | SR-CODE-EXP-069 | nested_block_context | { { ${7*7};echo${IFS}; }; } | Other Attacks | 0.810058 | HIGH |
| SR-CODE-R2-167 | SR-CODE-EXP-069 | operator_chain | ${7*7};echo${IFS} && printf '%s' CYBERTRACE_TEST || printf '%s' CYBERTRACE_TEST | SQL Injection | 0.998960 | CRITICAL |
| SR-CODE-R2-169 | SR-CODE-EXP-070 | nested_expression | ( ${7*7};ECHO; printf '%s' CYBERTRACE_TEST ) | SQL Injection | 0.635776 | MEDIUM |
| SR-CODE-R2-170 | SR-CODE-EXP-070 | block_wrapper | function CYBERTRACE_R2_170(){ printf '%s' CYBERTRACE_TEST; }; ${7*7};ECHO | Other Attacks | 0.450452 | LOW |
| SR-CODE-R2-171 | SR-CODE-EXP-070 | separator_expression | ${7*7};ECHO; printf '%s' CYBERTRACE_TEST | Other Attacks | 0.560835 | MEDIUM |
| SR-CODE-R2-172 | SR-CODE-EXP-073 | line_break_boundary | ${7*7};echo; printf CYBERTRACE_TEST
printf '%s' CYBERTRACE_TEST | Other Attacks | 0.732677 | MEDIUM |
| SR-CODE-R2-173 | SR-CODE-EXP-073 | quote_form_rewrite | printf "%s" CYBERTRACE_TEST; ${7*7};echo; printf CYBERTRACE_TEST | SQL Injection | 0.734113 | MEDIUM |
| SR-CODE-R2-175 | SR-CODE-EXP-076 | comment_boundary | ${7*7};echo%09 # CYBERTRACE_R2_175
printf '%s' CYBERTRACE_TEST | SQL Injection | 0.992771 | CRITICAL |
| SR-CODE-R2-176 | SR-CODE-EXP-076 | argument_rewrite | $(printf '%s' CYBERTRACE_TEST); ${7*7};echo%09 | SQL Injection | 0.834002 | HIGH |
| SR-CODE-R2-177 | SR-CODE-EXP-076 | computed_call_wrapper | { printf '%s' CYBERTRACE_TEST; }; ${7*7};echo%09 | Other Attacks | 0.612022 | MEDIUM |
| SR-CODE-R2-178 | SR-CODE-EXP-077 | alternate_delimiter | [ (${7*7})${IFS} ]; printf '%s' CYBERTRACE_TEST | SQL Injection | 0.993878 | CRITICAL |
| SR-CODE-R2-179 | SR-CODE-EXP-077 | case_marker_context | CYBERTRACEFLAG179=6; (${7*7})${IFS} | SQL Injection | 0.782939 | MEDIUM |
| SR-CODE-R2-180 | SR-CODE-EXP-077 | nested_block_context | { { (${7*7})${IFS}; }; } | SQL Injection | 0.711388 | MEDIUM |
| SR-CODE-R2-181 | SR-CODE-EXP-081 | operator_chain | (${7*7}); printf CYBERTRACE_TEST && printf '%s' CYBERTRACE_TEST || printf '%s' CYBERTRACE_TEST | SQL Injection | 0.998964 | CRITICAL |
| SR-CODE-R2-185 | SR-CODE-EXP-087 | quote_form_rewrite | {{ "CYBERTRACE_TEST" }}; ((#{7*7})) | SQL Injection | 0.486731 | LOW |
| SR-CODE-R2-187 | SR-CODE-EXP-089 | argument_rewrite | {{ (7+7) }}; (#{7*7}); 2+2 | SQL Injection | 0.974162 | CRITICAL |
| SR-CODE-R2-189 | SR-CODE-EXP-090 | case_marker_context | {{ cYBERtRACEfLAG189|[(#{7*7})] }} | Other Attacks | 0.566024 | MEDIUM |
| SR-CODE-R2-190 | SR-CODE-EXP-090 | nested_block_context | {{ {%raw%} [(#{7*7})] {%endraw%} }} | SQL Injection | 0.749921 | MEDIUM |
| SR-CODE-R2-192 | SR-CODE-EXP-092 | nested_expression | {{ ((#{7*7})%0a) + (5*1) }} | SQL Injection | 0.997444 | CRITICAL |
| SR-CODE-R2-196 | SR-CODE-EXP-094 | comment_boundary | {{7*7}};ECHO # CYBERTRACE_R2_196
printf '%s' CYBERTRACE_TEST | SQL Injection | 0.605071 | MEDIUM |
| SR-CODE-R2-197 | SR-CODE-EXP-097 | computed_call_wrapper | { printf '%s' CYBERTRACE_TEST; }; {{7*7}};echo; printf CYBERTRACE_TEST | SQL Injection | 0.591708 | MEDIUM |
| SR-CODE-R2-198 | SR-CODE-EXP-097 | alternate_delimiter | [ {{7*7}};echo; printf CYBERTRACE_TEST ]; printf '%s' CYBERTRACE_TEST | SQL Injection | 0.905931 | CRITICAL |
| SR-CODE-R2-199 | SR-CODE-EXP-100 | nested_block_context | { { {{7*7}};echo%09; }; } | Other Attacks | 0.841368 | HIGH |
| SR-CODE-R2-200 | SR-CODE-EXP-100 | operator_chain | {{7*7}};echo%09 && printf '%s' CYBERTRACE_TEST || printf '%s' CYBERTRACE_TEST | SQL Injection | 0.999171 | CRITICAL |

## Retention

The exact 70 seed cases are in the separate seed snapshot. The raw JSON result retains every full payload, source seed, mutation, prediction, confidence, WAF status, transaction, and bridge correlation.
