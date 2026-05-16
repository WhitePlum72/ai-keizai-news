// scripts/post-to-x.mjs
// 新記事のfrontmatterを読み取り、Xに自動投稿するスクリプト

import { TwitterApi } from 'twitter-api-v2';
import matter from 'gray-matter';
import fs from 'fs';
import path from 'path';

// ----------------------------
// 設定（ここを変えるだけでOK）
// ----------------------------
const BUZZ_SCORE_THRESHOLD = 50; // この値以上の記事のみ投稿
const SITE_URL = process.env.SITE_URL || 'https://ai-daily-jp.vercel.app';

// ----------------------------
// ファイルパスを引数から取得
// ----------------------------
const filePath = process.argv[2];

if (!filePath) {
  console.error('使い方: node post-to-x.mjs <記事ファイルパス>');
  process.exit(1);
}

if (!fs.existsSync(filePath)) {
  console.error(`ファイルが見つかりません: ${filePath}`);
  process.exit(1);
}

// ----------------------------
// frontmatterを読み取る
// ----------------------------
const fileContent = fs.readFileSync(filePath, 'utf-8');
const { data: frontmatter } = matter(fileContent);

const {
  title,
  article_slug,
  category_slug,
  buzz_score,
  source,
} = frontmatter;

if (!title || !article_slug || !category_slug) {
  console.error('必要なfrontmatterフィールド（title, article_slug, category_slug）が不足しています');
  process.exit(1);
}

// ----------------------------
// buzz_scoreフィルタリング
// ----------------------------
const score = parseFloat(buzz_score) || 0;

if (score < BUZZ_SCORE_THRESHOLD) {
  console.log(`⏭️  スキップ: buzz_score ${score} < ${BUZZ_SCORE_THRESHOLD} (${title})`);
  process.exit(0);
}

console.log(`✅ 投稿対象: buzz_score ${score} >= ${BUZZ_SCORE_THRESHOLD}`);

// ----------------------------
// 投稿テキストを生成
// ----------------------------
const articleUrl = `${SITE_URL}/article/${category_slug}/${article_slug}`;

const tweetText = buildTweet(title, articleUrl);

function buildTweet(title, url) {
  // 280文字制限を考慮
  const base = `\n${url}`;
  const maxTitleLength = 280 - base.length - 5;
  const shortTitle = title.length > maxTitleLength
    ? title.slice(0, maxTitleLength) + '…'
    : title;

  return `${shortTitle}${base}`;
}

// ----------------------------
// X APIクライアントを初期化
// ----------------------------
const client = new TwitterApi({
  appKey: process.env.TWITTER_CONSUMER_KEY,
  appSecret: process.env.TWITTER_CONSUMER_SECRET,
  accessToken: process.env.TWITTER_ACCESS_TOKEN,
  accessSecret: process.env.TWITTER_ACCESS_TOKEN_SECRET,
});

// ----------------------------
// 投稿実行
// ----------------------------
try {
  console.log('投稿内容:');
  console.log('---');
  console.log(tweetText);
  console.log('---');

  const tweet = await client.v2.tweet(tweetText);
  console.log(`✅ 投稿成功！ Tweet ID: ${tweet.data.id}`);
  console.log(`🔗 ${articleUrl}`);
} catch (error) {
  console.error('❌ 投稿失敗:', error.message);
  if (error.data) {
    console.error('APIエラー詳細:', JSON.stringify(error.data, null, 2));
  }
  process.exit(1);
}
