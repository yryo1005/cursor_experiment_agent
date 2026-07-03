@cursor_template/root_prompt.md の指示に従いプログラムは作成してください

このリポジトリで作成したAIエージェントは下記のように配置されて使用する予定です
プログラムはorder_dir, report_dir, log_dir, template_dirを引数とさせてください

# ディレクトリ構造の例
```text
.
├── cursor-template/         # cursorへの指示等やTeXレポートのテンプレートをまとめたリポジトリ
│   ├── root_prompt.md       # プログラムの指示が書かれたドキュメント
|   ├── prompts/             # それぞれのタスクの指示が書かれたプロンプトがまとめられたフォルダ
│   │   ├── environment_construction_prompt.md      # 環境構築の指示が書かれたドキュメント
│   │   ├── machine_learning_prompt.md              # AIの学習の指示が書かれたドキュメント
|   └── src/                 # それぞれのタスクの便利関数がまとめられたフォルダ
│       └── machine_learning_utils.py               # AIの学習で使用する便利関数がまとめられたファイル
│
├── cursor-TeX-templates/    # TeXテンプレートがまとめられたフォルダ
│   ├── report_template      # レポートのテンプレート
│   │   ├── main.tex         # latexでコンパイルするソース
│   │   ├── sections/        # レポートの章ごとに分けられたソースをまとめたフォルダ
│   │   │   └── 01_introdcution.tex                 # ソースは章ごとに分割する
│   │   └── figures/         # レポートの画像をまとめたフォルダ
│   └── slide_template       # スライドのテンプレート
│       ├── main.tex         # latexでコンパイルするソース
│       ├── sections/        # スライドの章ごとに分けられたソースをまとめたフォルダ
│       │   └── 01_introdcution.tex                 # ソースは章ごとに分割する
│       └── figures/         # スライドの画像をまとめたフォルダ
│
├── Experiment_Agent_v2/ # 実験レポートから次の実験を指示するAIエージェントのリポジトリ ★このリポジトリ
│   ├── src                  # ソースファイルをまとめたフォルダ
│   ├── .venv_{環境名}            # 仮想環境には明示的に名前を付ける
│   ├── requirements_{環境名}.txt # 依存ライブラリとバージョンを固定
│   └── run_agent.py         # 実験の指示を作成するプログラム
│
├── orders/                  # cursorへの指示がまとめられたフォルダ
│   ├── order_000.md         # 通し番号は0から始まる
│   ├── order_001.md
│   └── ...         
│
├── reports/                 # cursorのレポートがまとめられたフォルダ
│   ├── report_000.md        # 通し番号は0から始まる
│   ├── report_001.md
│   └── ...     
│
├── logs/                    # AIエージェントの会話ログがまとめられたフォルダ
│   ├── log_000.md           # 通し番号は0から始まる
│   ├── log_001.md
│   └── ...     
│
├── .gitignore               # outputs/ や datasets/，.venv/ を除外
│
├── .venv_{環境名}            # 仮想環境には明示的に名前を付ける
├── requirements_{環境名}.txt # 依存ライブラリとバージョンを固定
│
├── datasets/                # データセットが格納されるフォルダ
│
├── ex001_mnist_cnn/         # 実験001: 全比較手法で共通の条件（例: MNISTに対するCNN）
│   ├── model.py             # この実験で使用するモデル構造（CNN）の定義
│   ├── utils.py             # load_dataloader, load_model, 各種関数を定義
│   └── train.ipynb          # ハイパーパラメータやseedのループを回して学習を実行する主体
│
├── ex002_cifar10/           # 実験002: （例: CIFAR-10に対する実験）
│   ├── model.py
│   ├── utils.py
│   └── train.ipynb
│
├── outputs/                 # 実験結果の出力先（.gitignoreに対象設定）
│   ├── ex001_mnist_cnn/
│   │   ├── SGD/             # 比較する手法 1
│   │   │   ├── 0.001_32/    # ハイパーパラメータ（学習率_バッチサイズ）
│   │   │   │   ├── 0/       # seed 0 の結果
│   │   │   │   │   ├── best_model.pth
│   │   │   │   │   └── log.json
│   │   │   │   └── 1/       # seed 1 の結果
│   │   │   │       ├── best_model.pth
│   │   │   │       └── log.json
│   │   │   └── 0.01_64/
│   │   │       └── ...
│   │   └── Adam/            # 比較する手法 2
│   │       └── ...
│   └── ex002_cifar10/
│       └── ...
│
├── visualize_result.ipynb   # outputs/ 内を走査して信頼区間付きグラフを描画するノートブック
├── document.md              # メインロジックやコード仕様を解説したドキュメント
└── REEDME.md                # このリポジトリの概要や使用方法をまとめたドキュメント
```