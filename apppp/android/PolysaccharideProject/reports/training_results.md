# Training Results

Generated: 2026-03-18 09:06:21

## Best Model: GradientBoosting

| Model | Accuracy | Precision | Recall | F1 | CV Mean | CV Std |
|-------|----------|-----------|--------|----|---------|--------|
| RandomForest | 0.7908 | 0.7931 | 0.7908 | 0.7883 | 0.8239±0.0110 |
| GradientBoosting | 0.8662 | 0.8690 | 0.8662 | 0.8657 | 0.8720±0.0114 |
| DecisionTree | 0.8354 | 0.8364 | 0.8354 | 0.8356 | 0.8476±0.0104 |
| KNN | 0.4154 | 0.4045 | 0.4154 | 0.4037 | 0.3866±0.0133 |
| SVM | 0.4923 | 0.4556 | 0.4923 | 0.4556 | 0.4706±0.0077 |
| LogisticRegression | 0.5062 | 0.4774 | 0.5062 | 0.4817 | 0.4872±0.0124 |
| MLP | 0.6231 | 0.6152 | 0.6231 | 0.6171 | 0.6159±0.0205 |


## GridSearchCV Tuning

**RandomForest**: Best params = `{'max_depth': None, 'min_samples_split': 2, 'n_estimators': 200}`, Tuned accuracy = `0.7908`

**GradientBoosting**: Best params = `{'learning_rate': 0.05, 'max_depth': 5, 'n_estimators': 100}`, Tuned accuracy = `0.8615`



## Configuration
- Train/Test split: 80% / 20% (stratified)
- CV: 5-fold StratifiedKFold
- Feature columns: 62
- Train samples: 2599
- Test samples: 650
