# Team Setup — dùng chung env & quyền nền tảng

Hướng dẫn để cả team chạy chung dự án. Có 2 phần: (A) **file .env** để chạy app,
(B) **quyền nền tảng** (Vercel/Supabase/HF) để deploy & quản lý.

> ⚠️ **KHÔNG commit `.env` thật lên git.** File `.env` đã nằm trong `.gitignore`.
> Chia sẻ qua kênh an toàn (1Password/Bitwarden, tin nhắn riêng có mã hóa), **không** dán vào group chat công khai.

---

## A. File .env (để chạy app)

1. `cp .env.sample .env`
2. Điền các key (bảng dưới). Người giữ infra (bạn) gửi file `.env` đã điền cho từng thành viên qua kênh an toàn.

| Biến | Lấy ở đâu | Quyền |
|------|-----------|-------|
| `DATABASE_URL` | Supabase → Project Settings → Database → Connection string (pooler, port 5432) | Full DB |
| `SUPABASE_DB_PASSWORD` | Mật khẩu DB đặt lúc tạo project | — |
| `HF_TOKEN` | huggingface.co/settings/tokens → **New token → type Write** | Full (write repos + spaces) |
| `EMBEDDING_PROVIDER` + key | Team chốt: `gemini` (aistudio.google.com/apikey) hoặc khác | — |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys (đặt spending cap) | — |

---

## B. Quyền nền tảng (deploy & quản lý) — cách cho team "full quyền"

Khuyến nghị: **mời thành viên vào từng nền tảng** (an toàn hơn share token cá nhân).

### Vercel (host UI + API)
- Vào **Vercel → Team `paperlessvaic` → Settings → Members → Invite** → nhập email đồng nghiệp → role **Member/Owner**.
- Cách khác (chia sẻ token): Account → **Settings → Tokens → Create** (scope Full Account). Dán vào `VERCEL_TOKEN` để deploy CLI. *(Token = full quyền, giữ kỹ.)*

### Supabase (database)
- Vào **Supabase → Organization `vaic2026` → Team → Invite member** → role **Owner/Administrator** = full quyền project.
- API keys full: Project Settings → **API → `service_role`** (bypass RLS — chỉ dùng server-side, đừng lộ).

### Hugging Face (model hub / Space)
- `HF_TOKEN` type **Write** = full quyền tạo/push repo & space dưới tài khoản.
- Muốn team chung: tạo **Organization** trên HF → invite thành viên → mọi người push chung org.

---

## C. Deploy (khi đã có đủ key)

```bash
# 1. Schema Supabase theo dim provider (vd Gemini 768)
python deploy/load_schema.py --ref <ref> --region ap-northeast-1 --secrets .env --dim 768 --drop

# 2. retrieval-api → Vercel Python
python deploy/build_vercel_api.py && cd deploy/.vercel-api-build && vercel deploy --prod --yes
#    set env trên Vercel: EMBEDDING_PROVIDER, <provider key>, DATABASE_URL, CORS_ORIGINS, ANTHROPIC_API_KEY

# 3. UI → Vercel  (đã deploy: https://paperless-ui.vercel.app)
cd paperless-ui && vercel deploy --prod --yes
#    set env: NUXT_RETRIEVAL_API_HOST=<api-url>, ANTHROPIC_API_KEY
```

Chi tiết kiến trúc: [ARCHITECTURE.md](ARCHITECTURE.md) · Deploy: [DEPLOY.md](DEPLOY.md)

---

## D. 2 domain dev / main (đồng nghiệp tự build)

| Branch | Domain | Cách deploy |
|--------|--------|-------------|
| `main` | **https://paperless-ui.vercel.app** | `git checkout main && ./deploy/deploy-ui.sh main` |
| `dev`  | **https://paperless-ui-dev.vercel.app** | `git checkout dev && ./deploy/deploy-ui.sh dev` |

**Chuẩn bị 1 lần / người:** được mời vào Vercel team `paperlessvaic` (bạn: Vercel → Team → Members → Invite) → chạy `vercel login`.

> **Nâng cấp lên "push là tự build" (khuyến nghị):** hiện `buildmarketplacee-png` chỉ có quyền *push* (không admin) trên `januaryofmine/VAIC2026`, nên **chưa nối được Vercel ↔ GitHub tự động**. Để mỗi lần `git push` tự deploy:
> 1. **Chủ repo `januaryofmine`** vào Vercel project `paperlessvaic/paperless-ui` → Settings → Git → **Connect** repo (cài Vercel GitHub App), đặt **Production Branch = main**.
> 2. Xong: push `main` → cập nhật `paperless-ui.vercel.app`; push `dev` → Vercel tự tạo URL preview cho nhánh dev.
> (Hoặc `januaryofmine` cấp **admin** cho `buildmarketplacee-png` để mình tự cấu hình.)

---

## Hiện trạng hạ tầng (đã dựng)
- **Supabase**: project `vaic-paperless` (Tokyo), pgvector + schema ✅
- **Vercel UI**: https://paperless-ui.vercel.app ✅ (backend chờ chốt embedding provider)
- **HF token**: Write ✅
- **Chờ**: embedding provider + `ANTHROPIC_API_KEY` → deploy retrieval-api → nối env → chạy end-to-end.
