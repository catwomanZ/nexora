# CATWOMAN · Nexora on Railway

اجرای **پنل رسمی Nexora + نود رسمی Nexora** در یک سرویس Railway، بدون تغییر دادن باینری یا رابط Nexora.

> CATWOMAN فقط نام و لایهٔ استقرار است. خود Nexora، لوگوها و اعلان‌های آن دست‌نخورده می‌مانند.

## چیزی که آماده است

- Nexora Panel و Nexora Node رسمی نسخه `0.0.4`
- یک کانتینر و یک سرویس Railway
- دیتابیس SQLite و گواهی‌ها روی Volume در `/data`
- پنل: `https://YOUR-DOMAIN/panel/`
- اشتراک‌ها: زیر مسیر `/sub/`
- کانفیگ پیش‌فرض: `VLESS + WebSocket` روی `/ws`
- TLS روی لبهٔ Railway و ارتباط داخلی nginx با نود
- ساخت خودکار Node، Inbound، Template و TLS Front از API رسمی Nexora
- بررسی SHA-256 باینری‌های رسمی هنگام Build
- مدیریت هم‌زمان panel، node و nginx با Supervisor

## استقرار با گوشی

1. این مخزن را در Railway با **Deploy from GitHub Repo** باز کن.
2. در Variables این Secret را اضافه کن:

   ```text
   CATWOMAN_ADMIN_PASSWORD=یک-رمز-قوی-حداقل-۱۲-کاراکتری
   ```

3. یک Volume بساز و دقیقاً روی این مسیر Mount کن:

   ```text
   /data
   ```

4. در Networking روی **Generate Domain** بزن.
5. یک Redeploy انجام بده. برنامه دامنه را از `RAILWAY_PUBLIC_DOMAIN` می‌گیرد.
6. پنل را باز کن:

   ```text
   https://YOUR-DOMAIN/panel/
   ```

نام کاربری پیش‌فرض:

```text
catwoman
```

رمز همان `CATWOMAN_ADMIN_PASSWORD` است.

### متغیرهای اختیاری

| متغیر | پیش‌فرض | کاربرد |
|---|---:|---|
| `CATWOMAN_ADMIN_USER` | `catwoman` | نام مدیر اصلی |
| `CATWOMAN_DOMAIN` | دامنهٔ عمومی Railway | اجبار دامنهٔ سفارشی؛ بدون `https://` هم قبول است |
| `TZ` | `Asia/Tehran` | منطقهٔ زمانی |

رمز مدیر در هر شروع از Variable بالا اعمال می‌شود. برای عوض کردن رمز، آن را در Railway تغییر بده و Redeploy کن؛ تغییر فقط داخل پنل در شروع بعدی بازنویسی می‌شود.

اگر سرویس قبل از ساخت دامنه اجرا شود، موقتاً با `localhost` بالا می‌آید. بعد از Generate Domain حتماً Redeploy کن تا لینک‌های کاربر با دامنهٔ درست ساخته شوند.

## استفاده

1. در پنل یک User بساز.
2. Nexora برای Inbound پیش‌فرض، لینک TLS روی دامنهٔ Railway می‌سازد.
3. لینک درست باید این موارد را داشته باشد:
   - `security=tls`
   - `type=ws`
   - `path=/ws`
   - پورت `443`
4. لینک اشتراک تولیدشده معمولاً شکلی مانند زیر دارد:

   ```text
   https://YOUR-DOMAIN/sub/sub/USER-ID
   ```

منابعی که Wrapper مدیریت می‌کند:

- Node: `CATWOMAN`
- Inbound: `catwoman-ws`
- Template: `CATWOMAN`
- Front: `CATWOMAN Railway TLS`

نام یا Tag این چهار مورد را عوض نکن؛ در هر شروع با دامنه و تنظیمات Railway هماهنگ می‌شوند. Userها و منابع دیگر دست‌نخورده می‌مانند.

## محدودیت مهم

این بسته فقط مسیر پیش‌فرض **VLESS over WebSocket** را برای دامنهٔ HTTP/HTTPS Railway آماده می‌کند.

- پشتیبانی همهٔ پروتکل‌های Nexora ادعا نمی‌شود.
- UDP و پورت‌های عمومی پویا از این دامنه عبور نمی‌کنند.
- برای پروتکل خام TCP باید TCP Proxy جدا و پورت داخلی ثابت تنظیم شود؛ در این نسخه خودکار نشده است.
- فقط یک Replica اجرا کن؛ SQLite، Volume و نود محلی برای چند Replica طراحی نشده‌اند.
- Volume روی `/data` الزامی است؛ بدون آن اطلاعات با Rebuild از بین می‌رود.
- لایسنس و محدودیت‌های رسمی Nexora همچنان برقرارند؛ Wrapper هیچ HWID یا License را دور نمی‌زند.

## وضعیت تست

موارد زیر محلی و با باینری رسمی `0.0.4` تأیید شده‌اند:

- اتصال mTLS پنل به نود و وضعیت `connected`
- اجرای listener پیش‌فرض روی پورت داخلی
- پاسخ WebSocket با کد `101`
- عبور واقعی ترافیک VLESS → TLS proxy → WebSocket → Nexora Node → اینترنت
- تولید لینک Nexora با `security=tls`

هنوز استقرار زندهٔ همین مخزن روی Railway و اتصال از یک گوشی واقعی انجام نشده؛ تا آن تست انجام نشود، موفقیت نهایی Railway/موبایل ادعا نمی‌شود. گزارش دقیق‌تر در [VALIDATION.md](VALIDATION.md) است.

## سلامت سرویس

```text
GET /healthz
```

خروجی سالم:

```json
{"status":"ok","service":"CATWOMAN Nexora"}
```

## نکتهٔ حقوقی

باینری‌ها داخل مخزن نیستند. Dockerfile آن‌ها را مستقیم از Release رسمی Nexora می‌گیرد و checksum رسمی/ثبت‌شده را بررسی می‌کند. جزئیات در [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) است.
