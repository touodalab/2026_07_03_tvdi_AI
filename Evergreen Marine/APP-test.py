# ============================================================
# 長榮海運 (2603) 明日漲跌 決策樹分類模型
# 來源 Notebook : 長榮海運演算法（特徵M20）.ipynb
# 資料來源     : stocks_202101_202607.xlsx
# ============================================================

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix,
)

# 設定中文字型 (Windows 微軟正黑體)
matplotlib.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

folder = os.path.dirname(os.path.abspath(__file__))
file_name = 'stocks_202101_202607.xlsx'
figure_dir = folder

# ============================================================
# 一、資料載入
# ============================================================
print("=" * 60)
print("一、資料載入")
print("=" * 60)

df = pd.read_excel(os.path.join(folder, file_name))
print(f"原始資料筆數：{df.shape[0]} 筆，欄位數量：{df.shape[1]} 個")

# ============================================================
# 二、資料前處理與特徵工程
# ============================================================
print("\n" + "=" * 60)
print("二、資料前處理與特徵工程")
print("=" * 60)

# 1. 缺失值處理：刪除 MA5~MA20 與 Unnamed: 12 欄位
drop_cols = [f'MA{i}' for i in range(5, 21)] + ['Unnamed: 12']
df = df.drop(columns=drop_cols, errors='ignore')
print("刪除後的欄位清單：")
print(df.columns.tolist())

# 2. 重複資料處理
duplicates = df[df.duplicated()]
print(f"\n重複資料筆數：{duplicates.shape[0]} 筆")
df_clean = df.copy()
df_clean = df_clean.drop_duplicates()
print(f"最終處理完成的資料筆數：{df_clean.shape[0]} 筆，欄位數量：{df_clean.shape[1]} 個")

# 3. 異常值處理 (IQR 與 Z-score 檢視，僅觀察不刪除)
colname = 'close'
Q1 = df[colname].quantile(0.25)
Q3 = df[colname].quantile(0.75)
IQR = Q3 - Q1
upper = Q3 + 1.5 * IQR
lower = Q1 - 1.5 * IQR
df1 = df[(df[colname] < lower) | (df[colname] > upper)]
print(f"\n[IQR] Q1:{Q1:.2f} Q3:{Q3:.2f} IQR:{IQR:.2f} upper:{upper:.2f} lower:{lower:.2f} "
      f"離群值:{df1.shape[0]} 筆")

mean = df[colname].mean()
std = df[colname].std()
df['z_score'] = (df[colname] - mean) / std
df_z_outliers = df[df['z_score'].abs() > 3]
print(f"[Z-score] Mean:{mean:.2f} Std:{std:.2f} 離群值:{df_z_outliers.shape[0]} 筆")
df = df.drop(columns=['z_score'], errors='ignore')

# 4. 特徵衍生 (技術分析指標)
df['MA_5'] = df['close'].rolling(window=5).mean()
df['BIAS_20'] = (df['close'] - df['20MA']) / df['20MA']
df['MA_diff'] = df['MA_5'] - df['20MA']
df['daily_return'] = df['close'].pct_change()
df['amplitude'] = (df['max'] - df['min']) / df['open']

# 5. 建立目標變數 target (明日收盤價 > 今日收盤價 → 1，否則 → 0)
df['next_close'] = df['close'].shift(-1)
df['target'] = (df['next_close'] > df['close']).astype(int)

print("\n--- 目標變數分佈統計 ---")
print(df['target'].value_counts())
print("比例分佈：")
print(df['target'].value_counts(normalize=True).map(lambda n: f"{n:.2%}"))

# 6. 移除因計算均線與 shift 產生的空值
df_clean = df.dropna().copy()

# ============================================================
# 三、特徵與目標變數分離
# ============================================================
print("\n" + "=" * 60)
print("三、特徵與目標變數分離")
print("=" * 60)

y = df_clean['target']
feature_list = [
    '20MA',
    'BIAS_20',       # 20日乖離率 (相對指標)
    'MA_diff',       # 均線差值 (衍生指標)
    'daily_return',  # 當日報酬率 (百分比)
    'amplitude',     # 振幅 (相對比例)
    'spread',        # 高低價差
    'week',          # 星期 (週期變數)
]
X = df_clean[feature_list]
print(f"特徵矩陣 X 的形狀 (筆數, 特徵數)：{X.shape}")
print(f"目標變數 y 的形狀 (筆數,)：{y.shape}")
print("傳入模型的最終特徵欄位：")
print(X.columns.tolist())

# ============================================================
# 四、資料集分割 (按時間順序 80% / 20%)
# ============================================================
print("\n" + "=" * 60)
print("四、資料集分割 (時序 80%/20%)")
print("=" * 60)

train_ratio = 0.8
train_size = int(len(X) * train_ratio)
X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]

print(f"原始資料總筆數：{len(X)} 筆")
print(f"訓練集 (Train Set) 筆數：{len(X_train)} 筆 ({len(X_train)/len(X):.1%})")
print(f"測試集 (Test Set)  筆數：{len(X_test)} 筆 ({len(X_test)/len(X):.1%})")
print(f"訓練集時間區間：{df_clean['date'].iloc[:train_size].min()} 至 {df_clean['date'].iloc[:train_size].max()}")
print(f"測試集時間區間：{df_clean['date'].iloc[train_size:].min()} 至 {df_clean['date'].iloc[train_size:].max()}")

# ============================================================
# 五、決策樹模型建構與訓練
# ============================================================
print("\n" + "=" * 60)
print("五、決策樹模型建構與訓練")
print("=" * 60)

model_bias = DecisionTreeClassifier(
    criterion='gini',
    max_depth=3,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=42,
)
model_bias.fit(X_train, y_train)

train_acc = model_bias.score(X_train, y_train)
test_acc = model_bias.score(X_test, y_test)
print(f"訓練集準確率 (In-Sample)：{train_acc:.4f}")
print(f"測試集準確率 (Out-of-Sample)：{test_acc:.4f}")

# ============================================================
# 六、網格搜尋與超參數調校 (TimeSeriesSplit)
# ============================================================
print("\n" + "=" * 60)
print("六、網格搜尋與超參數調校 (TimeSeriesSplit)")
print("=" * 60)

param_grid = {
    'criterion': ['gini', 'entropy'],
    'max_depth': [3, 4, 5, 6, 8],
    'min_samples_split': [5, 10, 20],
    'min_samples_leaf': [2, 5, 10],
}
tscv = TimeSeriesSplit(n_splits=5)
grid_search = GridSearchCV(
    estimator=DecisionTreeClassifier(random_state=42),
    param_grid=param_grid,
    cv=tscv,
    scoring='accuracy',
    n_jobs=-1,
    verbose=0,
)
grid_search.fit(X_train, y_train)
best_model = grid_search.best_estimator_

print(f"最佳準確率 (CV Score)：{grid_search.best_score_:.4f}")
print("最佳超參數組合：")
print(grid_search.best_params_)
best_y_pred = best_model.predict(X_test)
print(f"最佳模型測試集準確率：{accuracy_score(y_test, best_y_pred):.4f}")

# ============================================================
# 七、模型評估
# ============================================================
print("\n" + "=" * 60)
print("七、模型評估")
print("=" * 60)

# 1. 不純度標準比較 (Gini vs Entropy)
model_gini = DecisionTreeClassifier(criterion='gini', max_depth=4, random_state=42)
model_entropy = DecisionTreeClassifier(criterion='entropy', max_depth=4, random_state=42)
model_gini.fit(X_train, y_train)
model_entropy.fit(X_train, y_train)
y_pred_gini = model_gini.predict(X_test)
y_pred_entropy = model_entropy.predict(X_test)

comparison_df = pd.DataFrame({
    '評估指標 (Metric)': ['準確率 (Accuracy)', '精確率 (Precision)', '召回率 (Recall)', 'F1 分數 (F1-Score)'],
    'Gini 不純度': [
        accuracy_score(y_test, y_pred_gini),
        precision_score(y_test, y_pred_gini),
        recall_score(y_test, y_pred_gini),
        f1_score(y_test, y_pred_gini),
    ],
    'Entropy (熵)': [
        accuracy_score(y_test, y_pred_entropy),
        precision_score(y_test, y_pred_entropy),
        recall_score(y_test, y_pred_entropy),
        f1_score(y_test, y_pred_entropy),
    ],
})
print("--- 不純度標準比較結果 ---")
print(comparison_df.to_string(index=False))
print(f"兩模型對測試集的預測結果是否完全相同：{np.array_equal(y_pred_gini, y_pred_entropy)}")

# 2. 混淆矩陣
y_pred = model_bias.predict(X_test)
cm = confusion_matrix(y_test, y_pred)
tn, fp, fn, tp = cm.ravel()
print("\n--- 混淆矩陣詳細數值 (model_bias) ---")
print(f"真負例 (TN) - 預測下跌且正確: {tn} 筆")
print(f"偽正例 (FP) - 預測上漲但實際下跌 (假訊號): {fp} 筆")
print(f"偽負例 (FN) - 預測下跌但實際上漲 (錯過行情): {fn} 筆")
print(f"真正例 (TP) - 預測上漲且正確: {tp} 筆")

fig, ax = plt.subplots(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=['下跌/平盤 (0)', '上漲 (1)'],
            yticklabels=['下跌/平盤 (0)', '上漲 (1)'], ax=ax)
ax.set_title('決策樹模型 - 混淆矩陣 (Confusion Matrix)')
ax.set_xlabel('模型預測結果 (Predicted Label)')
ax.set_ylabel('實際真實結果 (True Label)')
fig.tight_layout()
fig.savefig(os.path.join(figure_dir, 'confusion_matrix.png'), dpi=150)
plt.close(fig)
print("混淆矩陣圖已儲存：confusion_matrix.png")

# 3. 分類報告
print("\n--- 分類報告 (model_bias) ---")
print(classification_report(y_test, y_pred, target_names=['下跌/平盤 (0)', '上漲 (1)']))

# ============================================================
# 八、特徵重要性分析
# ============================================================
print("\n" + "=" * 60)
print("八、特徵重要性分析")
print("=" * 60)

importances = model_bias.feature_importances_
feature_importance_df = pd.DataFrame({
    'Feature': X_train.columns,
    'Importance': importances,
}).sort_values(by='Importance', ascending=False).reset_index(drop=True)
print(feature_importance_df.to_string(index=False))

fig, ax = plt.subplots(figsize=(10, 6))
sns.barplot(data=feature_importance_df, x='Importance', y='Feature',
            hue='Feature', legend=False, palette='viridis', ax=ax)
ax.set_title('決策樹特徵重要性分析 (Feature Importance)', fontsize=14)
ax.set_xlabel('重要性權重 (Importance Weight)', fontsize=12)
ax.set_ylabel('特徵名稱 (Features)', fontsize=12)
for index, value in enumerate(feature_importance_df['Importance']):
    ax.text(value + 0.005, index, f"{value:.4f}", va='center', fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(figure_dir, 'feature_importance.png'), dpi=150)
plt.close(fig)
print("特徵重要性圖已儲存：feature_importance.png")

# ============================================================
# 九、決策樹結構圖
# ============================================================
print("\n" + "=" * 60)
print("九、決策樹結構圖")
print("=" * 60)

fig, ax = plt.subplots(figsize=(16, 10))
plot_tree(
    model_bias,
    feature_names=X_train.columns.tolist(),
    class_names=['下跌/平盤 (0)', '上漲 (1)'],
    filled=True,
    rounded=True,
    fontsize=10,
    ax=ax,
)
ax.set_title("決策樹分類模型結構圖 (Decision Tree Structure)")
fig.tight_layout()
fig.savefig(os.path.join(figure_dir, 'decision_tree.png'), dpi=300)
plt.close(fig)
print("決策樹結構圖已儲存：decision_tree.png")

# ============================================================
# 十、明日走勢預測
# ============================================================
print("\n" + "=" * 60)
print("十、明日走勢預測")
print("=" * 60)

latest_feature = X.iloc[[-1]]
latest_date = df_clean['date'].iloc[-1]
tomorrow_pred = model_bias.predict(latest_feature)[0]
tomorrow_prob = model_bias.predict_proba(latest_feature)[0]

print(f"最新數據日期: {latest_date}")
print(f"模型的預測類別 (Prediction): {tomorrow_pred}")
if tomorrow_pred == 1:
    print("策略訊號: 【買進 / 看漲】")
else:
    print("策略訊號: 【觀望 / 看跌或平盤】")
print(f"下跌/平盤機率 (Class 0): {tomorrow_prob[0] * 100:.2f}%")
print(f"上漲機率 (Class 1)    : {tomorrow_prob[1] * 100:.2f}%")
print("\n模型完成。")
