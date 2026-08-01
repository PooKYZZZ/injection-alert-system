# Final Confirmatory Training Results Report

## Scope

This report was rebuilt from the full completed run directory: `ml_model\results\benchmarks\v3_907k_cleaned_final_confirmatory_weighted_ce_3seed_20260412_035441`

It uses the full result set, not only the top-level summary files. The report was generated after reading run-level artifacts, aggregate CSVs, all 9 seed summaries, all 9 training histories, all 9 calibration summaries, all 9 latency summaries, all 9 security summaries, and all 3 per-class aggregate files.

## Run Completion and Integrity

- Run name: `v3_907k_cleaned_final_confirmatory_weighted_ce_3seed`
- Dataset version: `v3_907k_cleaned`
- Completed models: distilbert, minilm_l6, tinybert_bigru_attn
- Failures recorded: `0`
- Deterministic mode: `True`
- Resume enabled: `True`
- Skip-completed enabled: `True`

This run directory is complete. All three models and all nine seed runs have final summaries, final aggregates, and full seed-level artifact packages.

## Dataset and Split Summary

| split      |   size | class_distribution                                                              |
|:-----------|-------:|:--------------------------------------------------------------------------------|
| train      | 159873 | SQL Injection 74,723; Other Attacks 49,546; Normal 29,991; Code Injection 5,613 |
| validation |  19661 | SQL Injection 9,138; Other Attacks 5,982; Normal 3,864; Code Injection 677      |
| test       |  19505 | SQL Injection 8,975; Other Attacks 6,035; Normal 3,658; Code Injection 837      |

Cross-split overlap checks from the manifest:

- `train_validation_overlap`: `0`
- `train_test_overlap`: `0`
- `validation_test_overlap`: `0`

## Top-Level Aggregate Results

| model_key           |   n_seeds |   best_epoch_mean |   best_epoch_std |   val_macro_f1_mean |   val_macro_f1_std |   test_macro_f1_mean |   test_macro_f1_std |   test_accuracy_mean |   test_accuracy_std |   test_ece_uncalibrated_mean |   test_ece_calibrated_mean |   normal_false_positive_rate_mean |   attack_escape_rate_mean |   inference_latency_mean_ms_mean |   training_workflow_runtime_sec_mean |
|:--------------------|----------:|------------------:|-----------------:|--------------------:|-------------------:|---------------------:|--------------------:|---------------------:|--------------------:|-----------------------------:|---------------------------:|----------------------------------:|--------------------------:|---------------------------------:|-------------------------------------:|
| minilm_l6           |         3 |           3.66667 |          0.57735 |            0.992468 |           0.000113 |             0.990434 |            0.003423 |             0.992429 |            0.00083  |                     0.002574 |                   0.004192 |                          0.00246  |                  0.002734 |                          10.7718 |                              732.262 |
| distilbert          |         3 |           3.33333 |          0.57735 |            0.993857 |           0.000418 |             0.989142 |            0.000331 |             0.992754 |            0.000263 |                     0.003047 |                   0.004356 |                          0.002551 |                  0.002019 |                          10.2975 |                             1830.03  |
| tinybert_bigru_attn |         3 |           4       |          0       |            0.993755 |           0.000121 |             0.988904 |            0.000394 |             0.992805 |            0.00018  |                     0.002926 |                   0.004645 |                          0.00164  |                  0.002146 |                          16.7074 |                             2094.66  |

This table is the shortest accurate summary of the benchmark. It shows aggregate central tendency and seed variability on the main evaluation, calibration, security, latency, and runtime metrics.

## Ranking by Metric

| metric                             | rank_1              | rank_2              | rank_3              |
|:-----------------------------------|:--------------------|:--------------------|:--------------------|
| test_macro_f1_mean                 | minilm_l6           | distilbert          | tinybert_bigru_attn |
| test_accuracy_mean                 | tinybert_bigru_attn | distilbert          | minilm_l6           |
| test_ece_uncalibrated_mean         | minilm_l6           | tinybert_bigru_attn | distilbert          |
| normal_false_positive_rate_mean    | tinybert_bigru_attn | minilm_l6           | distilbert          |
| attack_escape_rate_mean            | distilbert          | tinybert_bigru_attn | minilm_l6           |
| inference_latency_mean_ms_mean     | distilbert          | minilm_l6           | tinybert_bigru_attn |
| training_workflow_runtime_sec_mean | minilm_l6           | distilbert          | tinybert_bigru_attn |

No single model is first on every metric. The rank ordering changes depending on whether the priority is macro F1, calibration, security-oriented error rates, latency, or training runtime.

## Seed-Level Full Results

### distilbert

|   seed |   best_epoch |   val_accuracy | val_balanced_accuracy   |   val_macro_f1 |   val_weighted_f1 |   test_accuracy | test_balanced_accuracy   |   test_macro_f1 |   test_weighted_f1 |   test_ece_uncalibrated |   test_ece_calibrated |   normal_false_positive_rate |   attack_escape_rate |   latency_mean_ms |   latency_p95_ms |   runtime_sec |   epoch_time_sec |   temperature |
|-------:|-------------:|---------------:|:------------------------|---------------:|------------------:|----------------:|:-------------------------|----------------:|-------------------:|------------------------:|----------------------:|-----------------------------:|---------------------:|------------------:|-----------------:|--------------:|-----------------:|--------------:|
|     42 |            3 |       0.993337 |                         |       0.993824 |          0.993346 |        0.992822 |                          |        0.989384 |           0.992842 |                0.002961 |              0.004182 |                     0.00164  |             0.002146 |          10.5095  |          11.0769 |       1835.11 |          432.499 |       1.37384 |
|   1337 |            3 |       0.992981 |                         |       0.993457 |          0.992991 |        0.992463 |                          |        0.988764 |           0.992487 |                0.003396 |              0.004695 |                     0.003554 |             0.002146 |          10.5061  |          10.8565 |       1828.24 |          431.007 |       1.38729 |
|   2026 |            4 |       0.993846 |                         |       0.994291 |          0.993853 |        0.992976 |                          |        0.989277 |           0.992998 |                0.002784 |              0.004192 |                     0.00246  |             0.001767 |           9.87686 |          10.4583 |       1826.75 |          430.483 |       1.37809 |

### minilm_l6

|   seed |   best_epoch |   val_accuracy | val_balanced_accuracy   |   val_macro_f1 |   val_weighted_f1 |   test_accuracy | test_balanced_accuracy   |   test_macro_f1 |   test_weighted_f1 |   test_ece_uncalibrated |   test_ece_calibrated |   normal_false_positive_rate |   attack_escape_rate |   latency_mean_ms |   latency_p95_ms |   runtime_sec |   epoch_time_sec |   temperature |
|-------:|-------------:|---------------:|:------------------------|---------------:|------------------:|----------------:|:-------------------------|----------------:|-------------------:|------------------------:|----------------------:|-----------------------------:|---------------------:|------------------:|-----------------:|--------------:|-----------------:|--------------:|
|     42 |            3 |       0.992116 |                         |       0.992556 |          0.992128 |        0.993386 |                          |        0.994381 |           0.993392 |                0.001762 |              0.004196 |                     0.002734 |             0.00265  |           10.5953 |          11.2383 |       731.415 |          170.998 |       1.37972 |
|   1337 |            4 |       0.991913 |                         |       0.99234  |          0.991927 |        0.992002 |                          |        0.988624 |           0.992023 |                0.002893 |              0.004182 |                     0.002734 |             0.002713 |           10.798  |          11.3491 |       732.576 |          171.224 |       1.39119 |
|   2026 |            4 |       0.992167 |                         |       0.992509 |          0.992177 |        0.9919   |                          |        0.988296 |           0.991921 |                0.003067 |              0.004197 |                     0.001914 |             0.00284  |           10.9223 |          13.1822 |       732.794 |          171.278 |       1.39551 |

### tinybert_bigru_attn

|   seed |   best_epoch |   val_accuracy | val_balanced_accuracy   |   val_macro_f1 |   val_weighted_f1 |   test_accuracy | test_balanced_accuracy   |   test_macro_f1 |   test_weighted_f1 |   test_ece_uncalibrated |   test_ece_calibrated |   normal_false_positive_rate |   attack_escape_rate |   latency_mean_ms |   latency_p95_ms |   runtime_sec |   epoch_time_sec |   temperature |
|-------:|-------------:|---------------:|:------------------------|---------------:|------------------:|----------------:|:-------------------------|----------------:|-------------------:|------------------------:|----------------------:|-----------------------------:|---------------------:|------------------:|-----------------:|--------------:|-----------------:|--------------:|
|     42 |            4 |       0.993083 |                         |       0.993618 |          0.993091 |        0.992617 |                          |        0.988449 |           0.992644 |                0.002999 |              0.004513 |                     0.001914 |             0.002209 |           16.7622 |          17.4669 |       2095.56 |          494.631 |       1.37446 |
|   1337 |            4 |       0.993337 |                         |       0.993843 |          0.993346 |        0.992976 |                          |        0.989149 |           0.992999 |                0.002887 |              0.00445  |                     0.001914 |             0.001893 |           16.773  |          17.331  |       2094.74 |          494.443 |       1.37573 |
|   2026 |            4 |       0.993286 |                         |       0.993805 |          0.993295 |        0.992822 |                          |        0.989114 |           0.992844 |                0.002892 |              0.004972 |                     0.001093 |             0.002335 |           16.5871 |          17.433  |       2093.68 |          494.18  |       1.37625 |

## Calibration and Probability Quality

| model_key           |   val_ece_uncalibrated |   val_ece_calibrated |   test_ece_uncalibrated |   test_ece_calibrated |   val_nll_uncalibrated |   val_nll_calibrated |   test_nll_uncalibrated |   test_nll_calibrated |   val_brier_uncalibrated |   val_brier_calibrated |   test_brier_uncalibrated |   test_brier_calibrated |   temperature |   val_ece_delta |   test_ece_delta |   val_nll_delta |   test_nll_delta |
|:--------------------|-----------------------:|---------------------:|------------------------:|----------------------:|-----------------------:|---------------------:|------------------------:|----------------------:|-------------------------:|-----------------------:|--------------------------:|------------------------:|--------------:|----------------:|-----------------:|----------------:|-----------------:|
| distilbert          |               0.002146 |             0.002869 |                0.003047 |              0.004356 |               0.018083 |             0.018831 |                0.017603 |              0.018337 |                      nan |                    nan |                       nan |                     nan |       1.37974 |        0.000723 |         0.00131  |        0.000748 |         0.000734 |
| minilm_l6           |               0.002633 |             0.002933 |                0.002574 |              0.004192 |               0.02395  |             0.024191 |                0.019526 |              0.021107 |                      nan |                    nan |                       nan |                     nan |       1.38881 |        0.0003   |         0.001618 |        0.000241 |         0.001582 |
| tinybert_bigru_attn |               0.001868 |             0.00259  |                0.002926 |              0.004645 |               0.018233 |             0.019222 |                0.017995 |              0.018886 |                      nan |                    nan |                       nan |                     nan |       1.37548 |        0.000722 |         0.001719 |        0.000989 |         0.000891 |

Calibration is not uniformly beneficial across every reported metric in this run. Mean calibrated test ECE and mean calibrated test NLL are slightly worse than the corresponding uncalibrated values for all three models. That should be reported plainly instead of assuming calibration is automatically an improvement.

## Per-Class Aggregate Results

### distilbert

|   label_id | label_name     |   precision_mean |   precision_std |   recall_mean |   recall_std |   f1_mean |   f1_std |   support_sum |
|-----------:|:---------------|-----------------:|----------------:|--------------:|-------------:|----------:|---------:|--------------:|
|          0 | Code Injection |         0.954028 |        0.001257 |      1        |     0        |  0.976473 | 0.000658 |          2511 |
|          1 | Normal         |         0.991306 |        0.000934 |      0.997449 |     0.00096  |  0.994368 | 0.0007   |         10974 |
|          2 | Other Attacks  |         0.98926  |        0.000709 |      0.992046 |     0.000331 |  0.990651 | 0.000214 |         18105 |
|          3 | SQL Injection  |         0.99955  |        0.000195 |      0.990641 |     0.000446 |  0.995076 | 0.000149 |         26925 |

### minilm_l6

|   label_id | label_name     |   precision_mean |   precision_std |   recall_mean |   recall_std |   f1_mean |   f1_std |   support_sum |
|-----------:|:---------------|-----------------:|----------------:|--------------:|-------------:|----------:|---------:|--------------:|
|          0 | Code Injection |         0.969594 |        0.026355 |      0.999204 |     0.00138  |  0.984043 | 0.012796 |          2511 |
|          1 | Normal         |         0.988264 |        0.000404 |      0.99754  |     0.000473 |  0.99288  | 8e-05    |         10974 |
|          2 | Other Attacks  |         0.988342 |        0.001209 |      0.992378 |     0.002987 |  0.990353 | 0.00088  |         18105 |
|          3 | SQL Injection  |         0.999213 |        0.000195 |      0.989749 |     0.000295 |  0.994458 | 5.7e-05  |         26925 |

### tinybert_bigru_attn

|   label_id | label_name     |   precision_mean |   precision_std |   recall_mean |   recall_std |   f1_mean |   f1_std |   support_sum |
|-----------:|:---------------|-----------------:|----------------:|--------------:|-------------:|----------:|---------:|--------------:|
|          0 | Code Injection |         0.951844 |        0.002481 |      0.999602 |     0.00069  |  0.975137 | 0.001177 |          2511 |
|          1 | Normal         |         0.990777 |        0.000966 |      0.99836  |     0.000473 |  0.994553 | 0.000358 |         10974 |
|          2 | Other Attacks  |         0.98964  |        0.000247 |      0.991881 |     0.000438 |  0.990759 | 0.000174 |         18105 |
|          3 | SQL Injection  |         0.99985  |        6.5e-05  |      0.990529 |     0.000193 |  0.995168 | 6.5e-05  |         26925 |

The per-class pattern is consistent across models: `Code Injection` is the weakest class by precision and F1, while `SQL Injection` and `Normal` are the strongest. That class-level gap is a real part of the benchmark result.

## Security-Oriented Metrics

| model_key           |   normal_fp_rate_mean |   normal_fp_rate_std |   attack_escape_rate_mean |   attack_escape_rate_std |   normal_predicted_attack_count_mean |   attack_predicted_as_normal_count_mean |
|:--------------------|----------------------:|---------------------:|--------------------------:|-------------------------:|-------------------------------------:|----------------------------------------:|
| distilbert          |              0.002551 |             0.00096  |                  0.002019 |                 0.000219 |                              9.33333 |                                 32      |
| minilm_l6           |              0.00246  |             0.000473 |                  0.002734 |                 9.6e-05  |                              9       |                                 43.3333 |
| tinybert_bigru_attn |              0.00164  |             0.000473 |                  0.002146 |                 0.000228 |                              6       |                                 34      |

The security-oriented differences are small. `tinybert_bigru_attn` has the lowest mean normal false positive rate. `distilbert` has the lowest mean attack escape rate. `minilm_l6` leads on mean test macro F1 and training runtime, but not on those two security-specific rates.

## Latency and Runtime

| model_key           |   lat_mean_mean |   lat_mean_std |   lat_p95_mean |   lat_p95_std |   lat_std_mean |   lat_std_std |   runtime_mean |   runtime_std |   epoch_time_mean |   epoch_time_std |   model_size_mb_mean |   measure_steps_mean |   latency_batch_size_mean |
|:--------------------|----------------:|---------------:|---------------:|--------------:|---------------:|--------------:|---------------:|--------------:|------------------:|-----------------:|---------------------:|---------------------:|--------------------------:|
| distilbert          |         10.2975 |       0.364279 |        10.7972 |      0.313512 |        1.0591  |      0.719254 |       1830.03  |      4.45691  |           431.33  |         1.04602  |             253.911  |                  200 |                         1 |
| minilm_l6           |         10.7718 |       0.165068 |        11.9232 |      1.09175  |        1.29204 |      0.280851 |        732.262 |      0.740984 |           171.167 |         0.148486 |              87.0259 |                  200 |                         1 |
| tinybert_bigru_attn |         16.7074 |       0.10435  |        17.4103 |      0.070771 |        1.75174 |      0.5064   |       2094.66  |      0.943142 |           494.418 |         0.226351 |             262.183  |                  200 |                         1 |

Latency and runtime split into two separate stories: `distilbert` has the lowest mean inference latency, while `minilm_l6` has the lowest mean training runtime. `tinybert_bigru_attn` is highest on both latency and runtime in this benchmark.

## Training History Summary

| model_key           |   seed |   epochs_ran |   epoch_1_train_loss |   final_epoch_train_loss |   epoch_1_val_macro_f1 |   final_epoch_val_macro_f1 |   final_epoch_val_loss |   final_epoch_time_sec |
|:--------------------|-------:|-------------:|---------------------:|-------------------------:|-----------------------:|---------------------------:|-----------------------:|-----------------------:|
| distilbert          |     42 |            4 |             0.123164 |                 0.012088 |               0.989764 |                   0.993593 |               0.018455 |                430.681 |
| distilbert          |   1337 |            4 |             0.121927 |                 0.011172 |               0.991103 |                   0.99309  |               0.019223 |                429.769 |
| distilbert          |   2026 |            4 |             0.123309 |                 0.011296 |               0.990763 |                   0.994291 |               0.016252 |                431.952 |
| minilm_l6           |     42 |            4 |             0.19873  |                 0.018922 |               0.975682 |                   0.992465 |               0.023354 |                171.124 |
| minilm_l6           |   1337 |            4 |             0.199819 |                 0.018939 |               0.985931 |                   0.99234  |               0.023395 |                171.084 |
| minilm_l6           |   2026 |            4 |             0.19218  |                 0.018376 |               0.98336  |                   0.992509 |               0.02308  |                171.346 |
| tinybert_bigru_attn |     42 |            4 |             0.117037 |                 0.012804 |               0.990484 |                   0.993618 |               0.01738  |                494.126 |
| tinybert_bigru_attn |   1337 |            4 |             0.125658 |                 0.012352 |               0.987735 |                   0.993843 |               0.01787  |                494.119 |
| tinybert_bigru_attn |   2026 |            4 |             0.127534 |                 0.012638 |               0.988889 |                   0.993805 |               0.01745  |                494.17  |

All seed histories show clean convergence. The runs stopped after 3 or 4 epochs depending on the checkpointing and early-stopping dynamics. None of the histories indicate divergence or unstable training.

## Tokenization and Preparation Costs

| model_key           | model_id                             |   max_seq_len |   tokenization_seconds |   tokenization_throughput_samples_per_sec |
|:--------------------|:-------------------------------------|--------------:|-----------------------:|------------------------------------------:|
| distilbert          | distilbert-base-uncased              |           128 |                6.58596 |                                   30221.7 |
| minilm_l6           | nreimers/MiniLM-L6-H384-uncased      |           128 |                7.23296 |                                   27518.3 |
| tinybert_bigru_attn | huawei-noah/TinyBERT_General_6L_768D |           128 |                8.01698 |                                   24827.2 |

Tokenization overhead is small relative to training runtime for all three models.

## Seed Artifact Coverage

| model_key           |   seed |   present_artifacts |   expected_artifacts |
|:--------------------|-------:|--------------------:|---------------------:|
| distilbert          |     42 |                  15 |                   15 |
| distilbert          |   1337 |                  15 |                   15 |
| distilbert          |   2026 |                  15 |                   15 |
| minilm_l6           |     42 |                  15 |                   15 |
| minilm_l6           |   1337 |                  15 |                   15 |
| minilm_l6           |   2026 |                  15 |                   15 |
| tinybert_bigru_attn |     42 |                  15 |                   15 |
| tinybert_bigru_attn |   1337 |                  15 |                   15 |
| tinybert_bigru_attn |   2026 |                  15 |                   15 |

## Bottom-Line Reading

- `minilm_l6` has the highest mean test macro F1 and the lowest mean training runtime in this run.
- `distilbert` has the lowest mean inference latency in this run.
- `tinybert_bigru_attn` has the highest mean latency and highest mean training runtime while remaining close on held-out accuracy and macro F1.
- The absolute performance gaps are small, so this should be described as a close benchmark with different strengths rather than a one-sided outcome.
- The full artifact set is present and supports deeper follow-up analysis on class behavior, calibration, thresholding, security errors, and latency.

## Threshold Recall Summary

The tables below summarize `per_class_recall_at_threshold.csv` across all three seeds for each model. Values are mean recall after applying the confidence threshold and requiring the prediction to be both correct and confident.

### distilbert

| label_name     |   recall_at_0.5 |   recall_at_0.7 |   recall_at_0.8 |   recall_at_0.9 |
|:---------------|----------------:|----------------:|----------------:|----------------:|
| Code Injection |        1        |        1        |        1        |        0.997212 |
| Normal         |        0.99672  |        0.993348 |        0.983598 |        0.98059  |
| Other Attacks  |        0.99061  |        0.984977 |        0.983706 |        0.97404  |
| SQL Injection  |        0.990492 |        0.990269 |        0.990232 |        0.990046 |

### minilm_l6

| label_name     |   recall_at_0.5 |   recall_at_0.7 |   recall_at_0.8 |   recall_at_0.9 |
|:---------------|----------------:|----------------:|----------------:|----------------:|
| Code Injection |        0.999204 |        0.998407 |        0.997611 |        0.997611 |
| Normal         |        0.997357 |        0.988701 |        0.981593 |        0.976854 |
| Other Attacks  |        0.991936 |        0.982215 |        0.981165 |        0.972107 |
| SQL Injection  |        0.989601 |        0.989229 |        0.988932 |        0.988264 |

### tinybert_bigru_attn

| label_name     |   recall_at_0.5 |   recall_at_0.7 |   recall_at_0.8 |   recall_at_0.9 |
|:---------------|----------------:|----------------:|----------------:|----------------:|
| Code Injection |        0.999602 |        0.999602 |        0.999204 |        0.996814 |
| Normal         |        0.997995 |        0.989885 |        0.984144 |        0.979224 |
| Other Attacks  |        0.991218 |        0.984203 |        0.982767 |        0.975918 |
| SQL Injection  |        0.990529 |        0.990269 |        0.990084 |        0.989712 |

## Confidence-Band Summary

These tables summarize `confidence_band_summary.csv` across seeds. `LOW`, `MEDIUM`, and `HIGH` refer to the score bands used in the notebook outputs. The values below are seed means.

### distilbert

| band   |   coverage |   accuracy |   macro_precision |   macro_recall |   macro_f1 |
|:-------|-----------:|-----------:|------------------:|---------------:|-----------:|
| HIGH   |   0.990737 |   0.996619 |          0.987284 |       0.997533 |   0.992274 |
| LOW    |   0.001196 |   0.54828  |          0.676984 |       0.571332 |   0.5181   |
| MEDIUM |   0.008066 |   0.58305  |          0.474151 |       0.539281 |   0.452621 |

### minilm_l6

| band   |   coverage |   accuracy |   macro_precision |   macro_recall |   macro_f1 |
|:-------|-----------:|-----------:|------------------:|---------------:|-----------:|
| HIGH   |   0.987507 |   0.997993 |          0.99788  |       0.998533 |   0.998206 |
| LOW    |   0.000376 |   0.685714 |          0.451852 |       0.533333 |   0.473369 |
| MEDIUM |   0.012117 |   0.547476 |          0.495065 |       0.586634 |   0.397537 |

### tinybert_bigru_attn

| band   |   coverage |   accuracy |   macro_precision |   macro_recall |   macro_f1 |
|:-------|-----------:|-----------:|------------------:|---------------:|-----------:|
| HIGH   |   0.99043  |   0.996635 |          0.987162 |       0.997487 |   0.99219  |
| LOW    |   0.000649 |   0.369481 |          0.225926 |       0.373232 |   0.238909 |
| MEDIUM |   0.008921 |   0.609208 |          0.596276 |       0.593477 |   0.483559 |

## Attack-To-Normal False Negative Summary

These tables summarize `attack_to_normal_fn.csv` across seeds. They show how often each attack class was incorrectly predicted as `Normal`.

### distilbert

| attack_label   |   predicted_as_normal |   false_negative_rate_to_normal |
|:---------------|----------------------:|--------------------------------:|
| Code Injection |                0      |                        0        |
| Other Attacks  |               17.6667 |                        0.002927 |
| SQL Injection  |               14.3333 |                        0.001597 |

### minilm_l6

| attack_label   |   predicted_as_normal |   false_negative_rate_to_normal |
|:---------------|----------------------:|--------------------------------:|
| Code Injection |                0      |                        0        |
| Other Attacks  |               21.6667 |                        0.00359  |
| SQL Injection  |               21.6667 |                        0.002414 |

### tinybert_bigru_attn

| attack_label   |   predicted_as_normal |   false_negative_rate_to_normal |
|:---------------|----------------------:|--------------------------------:|
| Code Injection |                     0 |                        0        |
| Other Attacks  |                    19 |                        0.003148 |
| SQL Injection  |                    15 |                        0.001671 |

## Confusion Matrices By Seed

Each matrix below comes directly from the per-seed `confusion_matrix.csv` file. Rows are true labels and columns are predicted labels.

### distilbert

#### Seed 42

| true_label     |   Code Injection |   Normal |   Other Attacks |   SQL Injection |
|:---------------|-----------------:|---------:|----------------:|----------------:|
| Code Injection |              837 |        0 |               0 |               0 |
| Normal         |                0 |     3652 |               4 |               2 |
| Other Attacks  |               28 |       19 |            5985 |               3 |
| SQL Injection  |               11 |       15 |              58 |            8891 |

#### Seed 1337

| true_label     |   Code Injection |   Normal |   Other Attacks |   SQL Injection |
|:---------------|-----------------:|---------:|----------------:|----------------:|
| Code Injection |              837 |        0 |               0 |               0 |
| Normal         |                2 |     3645 |               9 |               2 |
| Other Attacks  |               28 |       18 |            5989 |               0 |
| SQL Injection  |               11 |       16 |              61 |            8887 |

#### Seed 2026

| true_label     |   Code Injection |   Normal |   Other Attacks |   SQL Injection |
|:---------------|-----------------:|---------:|----------------:|----------------:|
| Code Injection |              837 |        0 |               0 |               0 |
| Normal         |                1 |     3649 |               6 |               2 |
| Other Attacks  |               29 |       16 |            5987 |               3 |
| SQL Injection  |               11 |       12 |              57 |            8895 |

### minilm_l6

#### Seed 42

| true_label     |   Code Injection |   Normal |   Other Attacks |   SQL Injection |
|:---------------|-----------------:|---------:|----------------:|----------------:|
| Code Injection |              835 |        0 |               2 |               0 |
| Normal         |                0 |     3648 |               7 |               3 |
| Other Attacks  |                0 |       21 |            6009 |               5 |
| SQL Injection  |                0 |       21 |              70 |            8884 |

#### Seed 1337

| true_label     |   Code Injection |   Normal |   Other Attacks |   SQL Injection |
|:---------------|-----------------:|---------:|----------------:|----------------:|
| Code Injection |              837 |        0 |               0 |               0 |
| Normal         |                0 |     3648 |               7 |               3 |
| Other Attacks  |               28 |       21 |            5984 |               2 |
| SQL Injection  |               11 |       22 |              62 |            8880 |

#### Seed 2026

| true_label     |   Code Injection |   Normal |   Other Attacks |   SQL Injection |
|:---------------|-----------------:|---------:|----------------:|----------------:|
| Code Injection |              837 |        0 |               0 |               0 |
| Normal         |                0 |     3651 |               7 |               0 |
| Other Attacks  |               30 |       23 |            5974 |               8 |
| SQL Injection  |               11 |       22 |              57 |            8885 |

### tinybert_bigru_attn

#### Seed 42

| true_label     |   Code Injection |   Normal |   Other Attacks |   SQL Injection |
|:---------------|-----------------:|---------:|----------------:|----------------:|
| Code Injection |              837 |        0 |               0 |               0 |
| Normal         |                3 |     3651 |               4 |               0 |
| Other Attacks  |               30 |       20 |            5984 |               1 |
| SQL Injection  |               12 |       15 |              59 |            8889 |

#### Seed 1337

| true_label     |   Code Injection |   Normal |   Other Attacks |   SQL Injection |
|:---------------|-----------------:|---------:|----------------:|----------------:|
| Code Injection |              836 |        0 |               1 |               0 |
| Normal         |                2 |     3651 |               4 |               1 |
| Other Attacks  |               28 |       17 |            5989 |               1 |
| SQL Injection  |               11 |       13 |              59 |            8892 |

#### Seed 2026

| true_label     |   Code Injection |   Normal |   Other Attacks |   SQL Injection |
|:---------------|-----------------:|---------:|----------------:|----------------:|
| Code Injection |              837 |        0 |               0 |               0 |
| Normal         |                1 |     3654 |               3 |               0 |
| Other Attacks  |               29 |       20 |            5985 |               1 |
| SQL Injection  |               11 |       17 |              58 |            8889 |

## Final Notes

This document is now designed to be standalone. Another reader or model does not need direct file access to recover the main aggregate results, seed-level results, per-class results, calibration behavior, threshold behavior, security behavior, latency/runtime behavior, or the per-seed confusion matrices.
