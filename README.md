# 王涛的博客

基于 [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) 搭建的个人博客，支持中英文双语。

## 本地开发

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# macOS / Linux: source venv/bin/activate

pip install -r requirements.txt
mkdocs serve
```

打开 http://127.0.0.1:8000/My-Blog/ 预览（路径由 `site_url` 决定）。

## 内容

- `docs/posts/`：个人文章
- `docs/红楼梦/`：一百二十回全文（公版作品，底本为维基文库）

## 写文章

1. 在 `docs/posts/` 下新建 `<slug>.md`，英文版为 `<slug>.en.md`（可省略，省略时回退中文）。
2. 在 `mkdocs.yml` 的 `nav` 中登记新文章。
3. 参考根目录的 `template.md` / `template.en.md` 获取写作模板。
4. 图片放在 `docs/images/` 或文章同级目录下。

## 部署

推送 `master` 分支后，GitHub Actions（`.github/workflows/ci.yml`）会自动执行 `mkdocs gh-deploy`，发布到 `gh-pages` 分支。

仓库 Settings → Pages 中的 Source 需设置为 `gh-pages` 分支。

线上地址：https://wangtaoknight.github.io/My-Blog/

## 目录结构

- `docs/`：站点内容
- `overrides/`：主题覆盖（含 Giscus 评论组件，默认关闭）
- `tools/import_hongloumeng.py`：从维基文库导入《红楼梦》全文的脚本
- `mkdocs.yml`：站点配置与导航
- `requirements.txt`：构建依赖

### 重新导入《红楼梦》

```bash
python tools/import_hongloumeng.py         # 下载缺失章回并重建目录/导航
python tools/import_hongloumeng.py --fix   # 仅清理已有的正文格式
```

## 致谢

站点框架参考自 [PKUFlyingPig/cs-self-learning](https://github.com/PKUFlyingPig/cs-self-learning)。
