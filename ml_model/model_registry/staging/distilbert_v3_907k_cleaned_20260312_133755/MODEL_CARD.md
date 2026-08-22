# DistilBERT Injection Detector

## Active version
- distilbert_v3_907k_cleaned_20260312_133755

## Summary metrics
- run_contract_sha256: dbcb9de46d34e4619ac88b5c2178f38a3662730beaf9c24ceb10a78bc2d79967
- dataset_version: v3_907k_cleaned_model_input_v2
- preprocessing_version: model-input-v2-redacted
- model_key: distilbert
- model_id: distilbert-base-uncased
- model_revision: 12040accade4e8a0f71eabdb258fecc2e7e948be
- tokenizer_id: distilbert-base-uncased
- model_config_sha256: d7187890f91fa8932729af9c0d8bea2007effc4b0610af6ca8efe1a8e3075d2b
- tokenizer_identity: same pinned revision as the model above
- architecture: distilbert_sequence_classification
- architecture_family: huggingface_sequence_classifier
- head_type: hf_sequence_classification_head
- model_class: DistilBertForSequenceClassification
- experiment_phase: controlled_backbone_benchmark
- loss_key: weighted_ce
- seed: 42
- best_epoch: 3
- val_accuracy: 0.9972205569785819
- val_balanced_accuracy: 0.9979356084144905
- val_macro_f1: 0.9969071339558178
- val_weighted_f1: 0.9972236384790267
- val_ece_uncalibrated: 0.0005478200467316816
- val_ece_calibrated: 0.0023257879591994353
- val_nll_uncalibrated: 0.00822458628017704
- val_nll_calibrated: 0.009529104988730103
- val_brier_uncalibrated: 0.004371621169592167
- val_brier_calibrated: 0.004418951231333969
- test_accuracy: 0.9971117166212534
- test_balanced_accuracy: 0.9978213124590298
- test_macro_f1: 0.9970610449471339
- test_weighted_f1: 0.9971135017621083
- test_ece_uncalibrated: 0.0008271398433872585
- test_ece_calibrated: 0.0023403919279088438
- test_nll_uncalibrated: 0.008583286750460349
- test_nll_calibrated: 0.009819227268067873
- test_brier_uncalibrated: 0.004380235083473707
- test_brier_calibrated: 0.004405364594208183
- normal_false_positive_rate: 0.0016538037486218302
- attack_escape_rate: 0.0020377666077978536
- inference_latency_mean_ms: 13.85675950019504
- inference_latency_std_ms: 3.797885060949698
- inference_latency_p50_ms: 12.453449999156874
- inference_latency_p95_ms: 21.012349994634853
- inference_latency_min_ms: 11.334400005580392
- inference_latency_max_ms: 38.7239000046975
- model_size_mb: 255.41896057128906
- training_workflow_runtime_sec: 1683.7851293087006
- mean_epoch_training_time_sec: 391.53096055984497

## Label names
- Code Injection
- Normal
- Other Attacks
- SQL Injection

## Version history
- Current active: distilbert_v3_907k_cleaned_20260312_133755
- Previous active archived as: distilbert_v3_907k_cleaned_20260312_133755_pre_laptop_20260812
