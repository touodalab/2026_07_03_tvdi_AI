export interface IrisInput {
  sepal_length: number
  sepal_width: number
  petal_length: number
  petal_width: number
}

export interface IrisOutput {
  prediction_id: number
  prediction_label: string
  probabilities: Record<string, number>
}

export interface TrainConfig {
  n_estimators: number
  max_depth: number
  test_size: number
  random_state: number
}

export interface TrainResult {
  status: string
  accuracy: number
  train_time: number
  feature_importances: Record<string, number>
  message: string
}

export type TabType = 'predict' | 'train'
