# Changelog

## Unreleased

- Added `article_webhook`, a receiver for the blog Website target at `/fopost/articles/`: verifies
  the delivery through the parent SDK, answers `article.test`, and hands each published article to
  the `ON_ARTICLE_PUBLISHED` callable and the new `article_published` signal
- Added the `WEBSITE_SECRET` and `ON_ARTICLE_PUBLISHED` settings
- `client.blog` is available through `fopost_django.client` with the parent SDK that ships it
