# リアルタイム翻訳ツール
英和・和英対応、漢字ひらがな変換機能(試験的)あり

## Installation
### 1: Anacondaでpython環境を作る
```
conda create --name [任意の仮想環境名] python=3.10
conda activate [任意の仮想環境名]
pip install -r requirements.txt
```
### 2: tesseract導入
以下を参考にした
```
https://qiita.com/ryome/items/16fc42854fe93de78a23
```
## Usage
```
conda activate [任意の仮想環境名]
python screenTranslator.py app [-options]
```
### options
--lang: スクリーンショット->textの変換用(OCR用)  
--input: google翻訳入力指定  
--output google翻訳出力指定  
  
和英変換
```
python screenTranslator.py app --lang='jpn' --input='ja' --output='en'
```
漢字ひらがな変換
```
python screenTranslator.py app --lang='jpn' --input='ja' --kanjiflag=True
```
