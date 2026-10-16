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
2. یک Railway Volume بساز و دقیقاً روی این مسیر Mount کن:

   ```text
   /data
   ```

3. در Networking روی **Generate Domain** بزن و پورت داخلی را `8080` انتخاب کن.
4. همان دامنه را باز کن. Wrapper در اولین درخواست، دامنهٔ Railway را خودکار تشخیص می‌دهد و Nexora را هماهنگ می‌کند؛ این مرحله ممکن است چند ثانیه طول بکشد.
5. پنل را باز کن:

   ```text
   https://YOUR-DOMAIN/panel/
   ```

برای دامنهٔ تولیدشدهٔ Railway هیچ Variable مربوط به دامنه و هیچ Redeploy اضافه‌ای لازم نیست.

ورود پیش‌فرض اولیه:

```text
Username: admin
Password: admin
```

این ورود ضعیف و فقط برای شروع است. بلافاصله در Railway → Variables این متغیر را اضافه کن و Redeploy بزن:

```text
CATWOMAN_ADMIN_PASSWORD=یک-رمز-قوی-جدید
```

رمز مدیر در هر شروع از Variable بالا اعمال می‌شود. برای تغییر دائمی رمز، Variable را در Railway عوض کن و Redeploy بزن؛ تغییر فقط داخل UI پنل در شروع بعدی بازنویسی می‌شود.

### متغیرهای اختیاری

| متغیر | پیش‌فرض | کاربرد |
|---|---:|---|
| `CATWOMAN_ADMIN_PASSWORD` | `admin` | رمز مدیر؛ بعد از ورود اول فوراً تغییر بده |
| `CATWOMAN_DOMAIN` | خالی؛ تشخیص خودکار | فقط برای اجبار دامنهٔ سفارشی؛ بدون `https://` هم قبول است |
| `TZ` | `Asia/Tehran` | منطقهٔ زمانی |

اگر سرویس قبل از ساخت دامنه اجرا شود، در حالت تشخیص خودکار منتظر می‌ماند. پس از Generate Domain فقط دامنه را باز کن؛ دامنه در Volume ذخیره می‌شود و در Restartهای بعدی هم باقی می‌ماند.

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

استقرار زندهٔ Railway، سلامت سرویس و بازشدن پنل تأیید شده است. تشخیص خودکار دامنهٔ بدون Variable فعلاً در کانتینر تمیز و Restart محلی تأیید شده و اتصال VPN از گوشی واقعی هنوز تست نشده است. گزارش دقیق‌تر در [VALIDATION.md](VALIDATION.md) است.

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
