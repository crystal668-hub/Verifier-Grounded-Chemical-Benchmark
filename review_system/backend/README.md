# VGB 题目审核系统后端

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn review_system.main:app --app-dir review_system/backend --reload
```

首次启动会创建开发者账号 `admin`，密码由 `REVIEW_ADMIN_PASSWORD` 设置（默认 `change-me-now`）。生产环境必须设置 `REVIEW_SECRET_KEY`、管理员密码并使用 HTTPS。数据库默认位于 `review_system/data/review.db`。
