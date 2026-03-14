import os

# 無視する重いディレクトリ
ignore_dirs = {'node_modules', '.git', '.next', '__pycache__', 'workspace', 'venv', '.venv'}

def print_tree(startpath):
    for root, dirs, files in os.walk(startpath):
        # 無視するディレクトリを除外
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        # 階層の深さを計算
        level = root.replace(startpath, '').count(os.sep)
        indent = '│   ' * level
        
        # フォルダ名を出力
        folder_name = os.path.basename(root) if root != '.' else 'ARK_ROOT'
        print(f'{indent}├── {folder_name}/')
        
        # ファイルを出力
        subindent = '│   ' * (level + 1)
        for f in files:
            # 隠しファイル（.DS_Storeなど）もノイズになるならここで除外可能
            if not f.startswith('.DS_Store'):
                print(f'{subindent}├── {f}')

if __name__ == '__main__':
    print_tree('.')