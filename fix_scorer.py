import re

with open("scorer.py", "r", encoding="utf-8") as f:
    content = f.read()

old = '''        selected_titles_ja.append(title_ja)
        # スコアリングした全記事にbuzz_scoreを書き込む（未選出もスコア保持）
    for row in scored:
        buzz_all, article_id_all = row[0], row[1]
        cursor.execute(
            "UPDATE articles SET buzz_score = ? WHERE id = ?",
            (round(buzz_all, 2), article_id_all)
        )
    for row in selected:
        buzz, article_id, title, company, \\
        primary_score, stype, label, is_official, tier1_official = row
        cursor.execute("""
            UPDATE articles
            SET buzz_score           = ?,
                primary_source_score = ?,
                source_type          = ?,
                source_label         = ?,
                official_source      = ?
            WHERE id = ?
        """, (
            round(buzz, 2),
            primary_score,
            stype,
            label,
            1 if is_official else 0,
            article_id,
        ))'''

new = '''        selected_titles_ja.append(title_ja)

    # 全スコアリング記事のbuzz_scoreを保存
    for row in scored:
        buzz_all, article_id_all = row[0], row[1]
        cursor.execute(
            "UPDATE articles SET buzz_score = ? WHERE id = ?",
            (round(buzz_all, 2), article_id_all)
        )

    # 選出記事に追加情報を書き込む
    for row in selected:
        buzz, article_id, title, company, \\
        primary_score, stype, label, is_official, _ = row
        cursor.execute("""
            UPDATE articles
            SET primary_source_score = ?,
                source_type          = ?,
                source_label         = ?,
                official_source      = ?
            WHERE id = ?
        """, (
            primary_score,
            stype,
            label,
            1 if is_official else 0,
            article_id,
        ))'''

if old in content:
    content = content.replace(old, new)
    with open("scorer.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("修正成功")
else:
    print("対象文字列が見つかりません")
