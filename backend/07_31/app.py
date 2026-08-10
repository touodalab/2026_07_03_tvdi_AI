import os,sys,joblib
from pprint import pprint

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# ==========================================
# 1. 載入模型與狀態管理
# ==========================================

model_path:str = os.path.join(current_dir, "salary_model.joblib")
MODEL_STATE:dict = {}

def load_model_state():
    global MODEL_STATE
    if not os.path.exists(model_path):
        print("未檢測到模型檔案，正在自動執行訓練以生成 salary_model.joblib...")
        try:
            from train_save import train_and_save_model
            train_and_save_model()
        except Exception as e:
            raise RuntimeError(f"自動訓練模型失敗: {str(e)}")

    # 載入模型與相關元數據
    model_data:dict = joblib.load(model_path)
    pprint(model_data)
    MODEL_STATE.clear()
    MODEL_STATE.update({
            "model": model_data["model"],
            "oe": model_data.get("oe"),
            "le": model_data.get("le"),
            "ohe": model_data["ohe"],
            "scaler": model_data["scaler"],
            "r2": model_data.get("r2", 0.8463),
            "coef": model_data.get("coef",[]),
            "intercept": model_data.get("intercept", 51.2286),
            "feature_names": model_data.get("feature_names",['YearsExperience', 'EducationLevel', 'City_城市A', 'City_城市B', 'City_城市C']),
            "feature_coefs": model_data.get("feature_coefs", {}),
            "model_type": model_data.get("model_type","LinearRegression"),
            "alpha": model_data.get("alpha", 1.0),
            "train_time": model_data.get("train_time", 0.01),
            "test_size": model_data.get("test_size", 0.2),
            "random_state": model_data.get("random_state", 76)
        }
    )

    print("模型與預處理器成功載入！目前 R² Score：", MODEL_STATE["r2"])


if __name__ == "__main__":
    load_model_state()