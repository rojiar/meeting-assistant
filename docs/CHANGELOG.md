# تاریخچه تغییرات — دستیار جلسه

این فایل با **هر تغییر مهم** در کد یا معماری به‌روز می‌شود. اسناد HTML و spec باید هم‌راستا بمانند.

| تاریخ | تغییر |
|--------|--------|
| ۱۴۰۵/۰۳/۲۴ | **نسخه انگلیسی:** UI در `/en/` + سه سند/PDF انگلیسی در `docs/en/` و `docs/pdf/en/` |
| ۱۴۰۵/۰۳/۲۳ | **uv + Logfire:** `pyproject.toml`/`uv.lock`، org EU `meetingassistant`، token در `.env` |
| ۱۴۰۵/۰۳/۲۳ | **Logfire MLOps:** رصد agent/FastAPI/HTTPX + spanهای ingest؛ `LOGFIRE_TOKEN` اختیاری در `.env` |
| ۱۴۰۵/۰۳/۲۳ | **Jira description غنی:** `detail` و `acceptance_criteria` در agent + قالب فارسی ساخت‌یافته برای issue |
| ۱۴۰۵/۰۳/۱۹ | **نمونه transcript چهارم:** `meeting-04-client-kickoff.txt` — جلسه kickoff کارفرما (۷۶ نوبت، scope pilot، دمو، امنیت) |
| ۱۴۰۵/۰۳/۱۹ | **بازساختاری اسناد:** ۵ سند فارسی → ۳ سند فارسی گسترش‌یافته (شرح/پیاده‌سازی/نقشه‌راه+آینده) برای ارائه دانشگاهی؛ ادغام نقشه اسپرینت و قابلیت‌های پیشرفته |
| ۱۴۰۵/۰۳/۱۶ | **تست facilitation:** schema، agent prompt، API، live Gemini — `test_facilitation.py` |
| ۱۴۰۵/۰۳/۱۶ | **نمونه transcript:** سه جلسه مصنوعی طولانی‌تر و پیچیده‌تر برای scrum، planning و review/retro |
| ۱۴۰۵/۰۳/۰۶ | **Spec آینده:** راهنمای برگزارکننده، هم‌راستایی SOW/قرارداد، sentiment — `قابلیت‌های-پیشرفته-آینده.html` + نمودار |
| ۱۴۰۵/۰۳/۰۶ | **Voice (Gemini):** `POST /api/transcribe` — آپلود/ضبط صوت → transcript؛ ingest متنی بدون تغییر |
| ۱۴۰۵/۰۳/۰۶ | **Sprint 2/3 lite:** برچسب/پروژه، فیلتر، داشبورد تسک‌ها، قالب تحلیل، نگاشت Jira |
| ۱۴۰۵/۰۳/۰۶ | **Sprint 3 lite:** نگاشت گوینده→Jira assignee، ذخیره jira_key، آمار مشارکت، حذف جلسه |
| ۱۴۰۵/۰۳/۰۶ | **نقشه اسپرینت:** `docs/نقشه-اسپرینت‌ها.html` + `future-sprints-roadmap.md` (بدون STT) |
| ۱۴۰۵/۰۳/۰۶ | **تست‌ها:** `test_database`, `test_api_sqlite`, `test_live_api` (HTTP + Gemini/Jira)؛ `run-all-tests.sh` |
| ۱۴۰۵/۰۳/۰۶ | **SQLite:** جلسات و خلاصه‌ها در `data/meetings.db` (مهاجرت خودکار از `data/meetings/*.json`) |
| ۱۴۰۵/۰۳/۰۶ | **ChromaDB** جایگزین JSON دستی + cosine در Python (`data/chroma/`) |
| ۱۴۰۵/۰۳/۰۶ | **RAG هوشمند:** سلام/احوال‌پرسی بدون بازیابی transcript؛ پاسخ طبیعی + footnote کوتاه (نه dump متن خام) |
| ۱۴۰۵/۰۳/۰۶ | **Jira انگلیسی:** `title_en` / `context_en` برای issueها (UI فارسی) |
| ۱۴۰۵/۰۳/۰۶ | **صفحه جلسه SSR:** بارگذاری داده از سرور Astro (رفع گیر کردن «در حال بارگذاری») |
| ۱۴۰۵/۰۳/۰۶ | **قانون Cursor:** `.cursor/rules/docs-on-change.mdc` — به‌روزرسانی خودکار اسناد با هر تغییر |
| ۱۴۰۵/۰۳/۰۶ | **مستندات:** هم‌خوان‌سازی ۳ HTML + design spec + README با Chroma/RAG/Jira EN |
| ۱۴۰۵/۰۳/۰۶ | Embedding: `gemini-embedding-001` |
| ۱۴۰۵/۰۳/۰۵ | MVP اولیه: FastAPI + Pydantic AI + Astro RTL + Jira KAN |
| ۱۴۰۵/۰۳/۰۵ | ۹۷ تست واحد + ۱۲ تست live API |
| ۱۴۰۵/۰۳/۰۵ | انتشار GitHub: `Rvin-zh/meeting-assistant` |

## اسناد مرتبط (همیشه هم‌خوان کنید)

| سند | مخاطب |
|-----|--------|
| [01-project-overview.html](01-project-overview.html) | چشم‌انداز، معماری، چارچوب AI-native |
| [02-implementation.html](02-implementation.html) | جزئیات فنی MVP |
| [03-roadmap-and-future-work.html](03-roadmap-and-future-work.html) | اسپرینت‌ها، قابلیت‌های پیشرفته، MLOps |
| [superpowers/specs/2026-05-26-meeting-assistant-design.md](superpowers/specs/2026-05-26-meeting-assistant-design.md) | Spec مهندسی |

## قانون نگهداری

پس از هر PR یا تغییر معماری:

1. یک خط به این CHANGELOG اضافه کنید.
2. بخش مربوط در HTML/spec را به‌روز کنید.
3. در صورت نیاز `README.md` را اصلاح کنید.
