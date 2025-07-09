import subprocess
import os
import random
import sys
import re

def download_niconico_video(url, output_dir="videos", cookies_file_path=None):
    """
    yt-dlpを使ってニコニコ動画をダウンロードします。
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    video_id_match = re.search(r'(sm|nm|so)(\d+)', url)
    if video_id_match:
        base_filename = video_id_match.group(0)
    else:
        base_filename = "niconico_video"

    # yt-dlpは自動的に正しい拡張子を付与するため、ここでは %(ext)s を使用
    download_target_path_pattern = os.path.join(output_dir, f"{base_filename}.%(ext)s")

    print(f"ニコニコ動画をダウンロード中: {url}...")
    cmd = [
        "yt-dlp",
        url,
        "--output", download_target_path_pattern,
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--verbose",
    ]
    if cookies_file_path and os.path.exists(cookies_file_path):
        cmd.extend(["--cookies", cookies_file_path])
        print(f"クッキーファイル {cookies_file_path} を使用します。")
    else:
        print("クッキーファイルは使用しません。")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # yt-dlpの出力から実際にダウンロードされたファイル名を抽出
        # 通常、'[Merger] Merging formats into "..."' の行に最終ファイル名が含まれる
        match = re.search(r'\[Merger\] Merging formats into "(.*?)"', result.stdout)
        if match:
            actual_downloaded_path = match.group(1)
            # パスが絶対パスでない場合を考慮して output_dir と結合
            if not os.path.isabs(actual_downloaded_path):
                actual_downloaded_path = os.path.join(os.getcwd(), actual_downloaded_path) # yt-dlpの出力はカレントディレクトリ基準の場合がある

            if os.path.exists(actual_downloaded_path):
                print(f"ダウンロード完了: {actual_downloaded_path}")
                return actual_downloaded_path
        
        # fallback: マージ出力が見つからない場合、output_dirをスキャン
        downloaded_files = [f for f in os.listdir(output_dir) if f.startswith(base_filename) and (f.endswith('.mp4') or f.endswith('.webm') or f.endswith('.flv') or f.endswith('.mkv'))]
        if downloaded_files:
            actual_downloaded_path = os.path.join(output_dir, downloaded_files[0])
            print(f"ダウンロード完了 (フォールバック): {actual_downloaded_path}")
            return actual_downloaded_path
        
        print(f"エラー: yt-dlpは完了しましたが、ファイルが見つかりません。")
        print("yt-dlpの完全な出力:\n", result.stdout)
        print("yt-dlpのエラー出力:\n", result.stderr)
        return None

    except subprocess.CalledProcessError as e:
        print(f"yt-dlpエラー: {e.stderr}")
        return None
    except Exception as e:
        print(f"ダウンロード中に予期せぬエラーが発生しました: {e}")
        return None

def datamosh_video(input_video_path, output_video_path, glitches_to_apply=5, glitch_strength=5000):
    """
    PythonとFFmpegを使って動画にデータモッシングを施します。
    """
    if not os.path.exists(input_video_path):
        print(f"エラー: 入力ファイルが見つかりません - {input_video_path}")
        sys.exit(1)

    temp_inter_video = "temp_inter.avi"
    temp_glitched_video = "temp_glitched.avi"

    print("ステップ1: Iフレーム間隔を広く設定し、AVIに変換中...")
    try:
        subprocess.run([
            "ffmpeg", "-i", input_video_path,
            "-vf", "setpts=PTS/1.0",
            "-q:v", "0",
            "-g", "99999", # Iフレーム間隔を非常に大きく設定
            "-f", "avi", temp_inter_video
        ], check=True, capture_output=True, text=True)
        print("一時AVIファイル作成完了。")
    except subprocess.CalledProcessError as e:
        print(f"FFmpegエラー (ステップ1): {e.stderr}")
        if os.path.exists(temp_inter_video):
            os.remove(temp_inter_video)
        sys.exit(1)

    print(f"ステップ2: バイナリ破損を {glitches_to_apply} 回適用中...")
    try:
        with open(temp_inter_video, "rb") as f:
            video_data = bytearray(f.read())

        video_size = len(video_data)
        print(f"ビデオデータサイズ: {video_size} バイト")

        # 少なくともビデオデータの5%はスキップする（ヘッダー等の破損を避けるため）
        min_offset = int(video_size * 0.05)
        if min_offset > video_size - glitch_strength - 1:
            min_offset = 0 # データが小さい場合はスキップしない

        for _ in range(glitches_to_apply):
            start_offset = random.randint(min_offset, video_size - glitch_strength - 1)
            if start_offset < 0:
                start_offset = 0
            end_offset = start_offset + glitch_strength

            for i in range(start_offset, min(end_offset, video_size)):
                video_data[i] = random.randint(0, 255)

            print(f"  破損適用: オフセット {start_offset} から {end_offset} ({glitch_strength} バイト)")

        with open(temp_glitched_video, "wb") as f:
            f.write(video_data)
        print("バイナリ破損適用完了。")

    except Exception as e:
        print(f"ファイル処理エラー (ステップ2): {e}")
        if os.path.exists(temp_inter_video):
            os.remove(temp_inter_video)
        if os.path.exists(temp_glitched_video):
            os.remove(temp_glitched_video)
        sys.exit(1)

    print("ステップ3: 破損したAVIファイルを最終出力形式に変換中...")
    try:
        subprocess.run([
            "ffmpeg", "-i", temp_glitched_video,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-y",
            output_video_path
        ], check=True, capture_output=True, text=True)
        print(f"データモッシュ完了: {output_video_path}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpegエラー (ステップ3): {e.stderr}")
        sys.exit(1)
    finally:
        if os.path.exists(temp_inter_video):
            os.remove(temp_inter_video)
        if os.path.exists(temp_glitched_video):
            os.remove(temp_glitched_video)
        print("一時ファイルを削除しました。")

if __name__ == "__main__":
    # コマンドライン引数からURLと設定を取得
    # python datamosh_script.py <url> <glitches> <strength>
    if len(sys.argv) < 4:
        print("使用法: python datamosh_script.py <ニコニコ動画URL> <グリッチ回数> <グリッチ強度>")
        sys.exit(1)

    input_url = sys.argv[1]
    glitches = int(sys.argv[2])
    strength = int(sys.argv[3])
    
    # オプションでクッキーファイルのパスを受け取る (GitHub Actionsでは基本的に使わない)
    cookies_file = None 
    if len(sys.argv) > 4:
        cookies_file = sys.argv[4]

    output_filename = 'glitched_video.mp4' # 出力ファイル名を固定
    
    download_dir = "downloaded_videos_temp"
    downloaded_path = download_niconico_video(input_url, download_dir, cookies_file_path=cookies_file)

    if downloaded_path:
        datamosh_video(downloaded_path, output_filename, glitches_to_apply=glitches, glitch_strength=strength)
        
        # ダウンロードした一時ファイルをクリーンアップ
        if os.path.exists(downloaded_path):
            os.remove(downloaded_path)
            print(f"一時ダウンロードファイル {downloaded_path} を削除しました。")
        
        # 一時ダウンロードディレクトリが空になったら削除
        if os.path.exists(download_dir) and not os.listdir(download_dir):
            os.rmdir(download_dir)
            print(f"空のダウンロードディレクトリ {download_dir} を削除しました。")
        
        # GitHub Actionsの次のステップで利用するために、出力ファイル名を標準出力に出力
        print(f"::set-output name=glitched_output_file::{output_filename}")
    else:
        print("動画のダウンロードに失敗しました。データモッシュをスキップします。")
        sys.exit(1)
