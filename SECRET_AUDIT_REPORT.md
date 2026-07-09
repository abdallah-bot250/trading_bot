# Secret Audit Report

Generated: 2026-07-09T05:41:14

Scope: source project scanned for tokens, API keys, database URLs, payment secrets, AdsGram secrets, personal emails, phone numbers, private URLs, env backups, and customer data indicators.

Production files were not deleted. The sale package is created as a separate sanitized copy.

| File | Type | Masked Value | Classification | Needs Cleaning | Included In Sale |
|---|---:|---|---|---:|---:|
| `.env.example` | email | `admin@....com` | placeholder | NO | YES |
| `.env.example` | email | `no-rep....com` | placeholder | NO | YES |
| `.env.example` | phone | `971556644297` | possible personal phone | YES | NO |
| `DEPLOYMENT.md` | email | `admin@....com` | placeholder | NO | YES |
| `DEPLOYMENT.md` | private_url | `http:/...ost`` | local/private deployment URL | YES | NO |
| `DEPLOYMENT.md` | private_url | `http:/...080`` | local/private deployment URL | YES | NO |
| `DEPLOYMENT.md` | private_url | `http:/...lth`` | local/private deployment URL | YES | NO |
| `Dockerfile` | phone | `127.0.0.1` | possible personal phone | YES | NO |
| `Dockerfile` | private_url | `http:/...alth` | local/private deployment URL | YES | NO |
| `LAUNCH_CHECKLIST.md` | phone | `2026-06-23` | possible personal phone | YES | NO |
| `auto_sender.py` | generic_secret_assignment | `os.env...EN")` | needs review | YES | NO |
| `auto_sender.py` | generic_secret_assignment | `secret...(32)` | needs review | YES | NO |
| `auto_sender.py` | generic_secret_assignment | `str(token` | needs review | YES | NO |
| `auto_sender.py` | generic_secret_assignment | `None,` | placeholder | NO | YES |
| `auto_sender.py` | generic_secret_assignment | `mapped_token` | needs review | YES | NO |
| `auto_sender.py` | generic_secret_assignment | `create..._id,` | needs review | YES | NO |
| `auto_sender.py` | generic_secret_assignment | `user_i...ey"]` | needs review | YES | NO |
| `auto_sender.py` | generic_secret_assignment | `api_key,` | needs review | YES | NO |
| `auto_sender.py` | phone | `1003722350505` | possible personal phone | YES | NO |
| `docker-compose.yml` | database_url_with_password | `postgr...xora` | possible real secret | YES | NO |
| `docker-compose.yml` | phone | `127.0.0.1` | possible personal phone | YES | NO |
| `docker-compose.yml` | private_url | `http:/...alth` | local/private deployment URL | YES | NO |
| `market_analyzer.py` | phone | `100 - (100` | possible personal phone | YES | NO |
| `market_analyzer.py` | phone | `0.0000001` | possible personal phone | YES | NO |
| `SAFETY_PATCH_CODEX_REPORT.md` | phone | `2026-07-04` | possible personal phone | YES | NO |
| `LAUNCH_FIX_REPORT_20260705.md` | phone | `2026-07-05` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | email | `admin@....com` | possible personal email | YES | NO |
| `SECRET_AUDIT_REPORT.md` | email | `your@email.com` | possible personal email | YES | NO |
| `SECRET_AUDIT_REPORT.md` | email | `K@Fo.QKBwrr` | possible personal email | YES | NO |
| `SECRET_AUDIT_REPORT.md` | email | `Ys@nU.Fr` | possible personal email | YES | NO |
| `SECRET_AUDIT_REPORT.md` | email | `g@M.QF` | possible personal email | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `2026-07-09` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `971556644297` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `127.0.0.1` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `2026-06-23` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `1003722350505` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `100 - (100` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `0.0000001` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `2026-07-04` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `2026-07-05` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `123456789` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `018543329` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `0 0 716 716` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `508.74....399` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `516.77....282` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `461.78....923` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `376.23....596` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `278.90....361` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `217.29....149` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `174.95....274` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `198.89....391` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `253.88...8.75` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `339.44....079` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `436.76....315` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `498.38....526` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `540.71....402` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `470.89....776` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `486.89....412` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `415.57....046` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `412.41....046` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `317.401 310.82` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `317.40....837` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `387.64....174` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `414.17....776` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `357.83....144` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `398.27....491` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `357.83....532` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `317.39....185` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `264.77....693` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `265.20....393` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `338.3 ....573` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `302.01....937` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `298.84....798` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `268.06....699` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `266.04....017` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `203.39....454` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `209.24....999` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `244.27....591` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `337.33....365` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `308.50....013` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `306.48...3.02` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `234.97....357` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `208.86....454` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `244.775 470.9` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `228.78....264` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `300.096 455.63` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `303.26...5.63` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `398.27....856` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `398.27....839` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `328.02....502` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `301.49...70.9` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `450.89....982` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `450.46....283` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `377.37....102` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `413.65....738` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `416.82....877` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `447.60....977` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `449.63....659` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `512.28....221` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `506.42....676` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `471.39....085` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `378.33....311` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `407.17 282.663` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `409.19....655` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `480.70....318` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `506.80....221` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `2026-06-27` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `260422155105` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `270423155104` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `251222181730` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `301221181730` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `202606...2183` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `260408174626` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `370709174626` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `21260409174626` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `260408174625` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `21260409174625` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `20260625172527` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `20260702172526` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `20160627172527` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `260102201415` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `270102201414` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `666666666` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `061321 55` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `020814 100` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `071321 44` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `061320 50` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `071525 52` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `071525 55` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `101827 52` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `971568869313` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `61591117963149` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `091512 100` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `0568869313` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `0 0 24 24` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `12.04 2.5` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `9.4 9....4.16` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `9.4 9....17.9` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `7.5 7....0 15` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `1.33 0...-.94` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `34-.19...-.36` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `7.5 7....11.6` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `18 0-....-.49` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `0-.65....3-.8` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `2.84 0...3.48` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `5199247792` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `2999-01-01` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `14566177920001` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `450030...0001` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `0 0 64 64` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `23 7 4...3 15` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `42 58 ...2 49` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `0 0 720 180` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `0 0 0 ...55 0` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `44 1 9...0 16` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `27 26-...11 7` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `000...00` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `888888...8888` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `999999...9999` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `0000000` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `111111111` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `00000` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `111...11` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `0004000` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `800...004` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `1001000` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `000...004` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `000...01` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `111111...1111` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `555555555558` | possible personal phone | YES | NO |
| `SECRET_AUDIT_REPORT.md` | phone | `556644297` | possible personal phone | YES | NO |
| `README.md` | telegram_token | `123456...xxxx` | possible real secret | YES | NO |
| `README.md` | email | `your@email.com` | possible personal email | YES | NO |
| `README.md` | phone | `127.0.0.1` | possible personal phone | YES | NO |
| `README.md` | phone | `123456789` | possible personal phone | YES | NO |
| `README.md` | private_url | `http:/...5000` | local/private deployment URL | YES | NO |
| `README.md` | private_url | `https:....app` | local/private deployment URL | YES | NO |
| `README.md` | private_url | `https:...hook` | local/private deployment URL | YES | NO |
| `static/nexora-live-hero.png` | phone | `018543329` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `0 0 716 716` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `508.74....399` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `516.77....282` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `461.78....923` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `376.23....596` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `278.90....361` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `217.29....149` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `174.95....274` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `198.89....391` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `253.88...8.75` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `339.44....079` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `436.76....315` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `498.38....526` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `540.71....402` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `470.89....776` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `486.89....412` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `415.57....046` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `412.41....046` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `317.401 310.82` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `317.40....837` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `387.64....174` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `414.17....776` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `357.83....144` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `398.27....491` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `357.83....532` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `317.39....185` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `264.77....693` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `265.20....393` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `338.3 ....573` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `302.01....937` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `298.84....798` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `268.06....699` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `266.04....017` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `203.39....454` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `209.24....999` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `244.27....591` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `337.33....365` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `308.50....013` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `306.48...3.02` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `234.97....357` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `208.86....454` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `244.775 470.9` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `228.78....264` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `300.096 455.63` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `303.26...5.63` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `398.27....856` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `398.27....839` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `328.02....502` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `301.49...70.9` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `450.89....982` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `450.46....283` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `377.37....102` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `413.65....738` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `416.82....877` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `447.60....977` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `449.63....659` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `512.28....221` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `506.42....676` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `471.39....085` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `378.33....311` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `407.17 282.663` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `409.19....655` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `480.70....318` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `506.80....221` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `2026-06-27` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `260422155105` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `270423155104` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `251222181730` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `301221181730` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `202606...2183` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `260408174626` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `370709174626` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `21260409174626` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `260408174625` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `21260409174625` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `20260625172527` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `20260702172526` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `20160627172527` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `260102201415` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `270102201414` | possible personal phone | YES | NO |
| `static/nexora-live-hero.png` | phone | `666666666` | possible personal phone | YES | NO |
| `static/nexora-global-bg.png` | email | `K@Fo.QKBwrr` | possible personal email | YES | NO |
| `static/nexora-global-bg.png` | email | `Ys@nU.Fr` | possible personal email | YES | NO |
| `static/nexora-global-bg.png` | email | `g@M.QF` | possible personal email | YES | NO |
| `static/premium.css` | phone | `2026-07-04` | possible personal phone | YES | NO |
| `static/premium.css` | phone | `061321 55` | possible personal phone | YES | NO |
| `static/premium.css` | phone | `020814 100` | possible personal phone | YES | NO |
| `static/premium.css` | phone | `071321 44` | possible personal phone | YES | NO |
| `static/premium.css` | phone | `061320 50` | possible personal phone | YES | NO |
| `static/premium.css` | phone | `071525 52` | possible personal phone | YES | NO |
| `static/premium.css` | phone | `071525 55` | possible personal phone | YES | NO |
| `templates/dashboard.html` | phone | `2026-07-04` | possible personal phone | YES | NO |
| `templates/invoice_history.html` | phone | `101827 52` | possible personal phone | YES | NO |
| `templates/landing.html` | phone | `971568869313` | possible personal phone | YES | NO |
| `templates/landing.html` | phone | `61591117963149` | possible personal phone | YES | NO |
| `templates/admin.html` | phone | `091512 100` | possible personal phone | YES | NO |
| `templates/dashboard_section.html` | phone | `971568869313` | possible personal phone | YES | NO |
| `templates/dashboard_section.html` | phone | `0568869313` | possible personal phone | YES | NO |
| `templates/dashboard_section.html` | phone | `61591117963149` | possible personal phone | YES | NO |
| `templates/support.html` | phone | `971568869313` | personal/support contact | YES | NO |
| `templates/support.html` | phone | `0 0 24 24` | personal/support contact | YES | NO |
| `templates/support.html` | phone | `12.04 2.5` | personal/support contact | YES | NO |
| `templates/support.html` | phone | `9.4 9....4.16` | personal/support contact | YES | NO |
| `templates/support.html` | phone | `9.4 9....17.9` | personal/support contact | YES | NO |
| `templates/support.html` | phone | `7.5 7....0 15` | personal/support contact | YES | NO |
| `templates/support.html` | phone | `1.33 0...-.94` | personal/support contact | YES | NO |
| `templates/support.html` | phone | `34-.19...-.36` | personal/support contact | YES | NO |
| `templates/support.html` | phone | `7.5 7....11.6` | personal/support contact | YES | NO |
| `templates/support.html` | phone | `18 0-....-.49` | personal/support contact | YES | NO |
| `templates/support.html` | phone | `0568869313` | personal/support contact | YES | NO |
| `templates/support.html` | phone | `61591117963149` | personal/support contact | YES | NO |
| `templates/support.html` | phone | `0-.65....3-.8` | personal/support contact | YES | NO |
| `templates/support.html` | phone | `2.84 0...3.48` | personal/support contact | YES | NO |
| `templates/company_page.html` | phone | `091512 100` | possible personal phone | YES | NO |
| `templates/company_page.html` | phone | `971568869313` | possible personal phone | YES | NO |
| `templates/company_page.html` | phone | `0568869313` | possible personal phone | YES | NO |
| `templates/company_page.html` | phone | `61591117963149` | possible personal phone | YES | NO |
| `trader_app/config.py` | generic_secret_assignment | `os.env...EY",` | needs review | YES | NO |
| `trader_app/config.py` | email | `no-rep....com` | placeholder | NO | YES |
| `scripts/smoke_routes.py` | private_url | `http:/...host` | local/private deployment URL | YES | NO |
| `scripts/telegram_webhook.py` | generic_secret_assignment | `requir...EN")` | needs review | YES | NO |
| `scripts/telegram_webhook.py` | private_url | `http:/...host` | local/private deployment URL | YES | NO |
| `scripts/diagnose_telegram_link.py` | private_url | `http:/...host` | local/private deployment URL | YES | NO |
| `scripts/diagnose_referral_and_messaging.py` | phone | `61591117963149` | possible personal phone | YES | NO |
| `scripts/diagnose_signal_pipeline_audit.py` | phone | `5199247792` | possible personal phone | YES | NO |
| `scripts/diagnose_signal_pipeline_audit.py` | phone | `2999-01-01` | possible personal phone | YES | NO |
| `scripts/diagnose_real_metrics_and_sale_readiness.py` | database_url_with_password | `postgr...*@",` | possible real secret | YES | NO |
| `scripts/diagnose_sale_package_clean.py` | phone | `556644297` | possible personal phone | YES | NO |
| `scripts/diagnose_sale_package_clean.py` | phone | `0568869313` | possible personal phone | YES | NO |
| `trader_app/blueprints/routes.py` | generic_secret_assignment | `token,` | needs review | YES | NO |
| `trader_app/blueprints/routes.py` | generic_secret_assignment | `create...n(c,` | needs review | YES | NO |
| `trader_app/blueprints/routes.py` | generic_secret_assignment | `genera...raw)` | needs review | YES | NO |
| `trader_app/blueprints/routes.py` | generic_secret_assignment | `(reque...rd")` | needs review | YES | NO |
| `trader_app/blueprints/routes.py` | generic_secret_assignment | `(token` | needs review | YES | NO |
| `trader_app/blueprints/routes.py` | generic_secret_assignment | `create...ail)` | needs review | YES | NO |
| `trader_app/blueprints/routes.py` | generic_secret_assignment | `token)` | needs review | YES | NO |
| `trader_app/blueprints/routes.py` | generic_secret_assignment | `%s,` | needs review | YES | NO |
| `trader_app/blueprints/routes.py` | generic_secret_assignment | `reques...ey",` | needs review | YES | NO |
| `trader_app/blueprints/routes.py` | generic_secret_assignment | `secret...(32)` | needs review | YES | NO |
| `trader_app/blueprints/routes.py` | generic_secret_assignment | `str(token` | needs review | YES | NO |
| `trader_app/blueprints/routes.py` | phone | `61591117963149` | possible personal phone | YES | NO |
| `trader_app/blueprints/routes.py` | phone | `0568869313` | possible personal phone | YES | NO |
| `trader_app/blueprints/routes.py` | phone | `971568869313` | possible personal phone | YES | NO |
| `trader_app/blueprints/routes.py` | phone | `14566177920001` | possible personal phone | YES | NO |
| `trader_app/blueprints/routes.py` | phone | `450030...0001` | possible personal phone | YES | NO |
| `trader_app/db/models.py` | generic_secret_assignment | `Column(Text,` | needs review | YES | NO |
| `trader_app/db/models.py` | generic_secret_assignment | `Column(Text)` | needs review | YES | NO |
| `trader_app/services/runtime.py` | generic_secret_assignment | `os.env...EN")` | needs review | YES | NO |
| `trader_app/services/runtime.py` | generic_secret_assignment | `sessio...en")` | needs review | YES | NO |
| `trader_app/services/runtime.py` | generic_secret_assignment | `secret...(32)` | needs review | YES | NO |
| `trader_app/services/runtime.py` | email | `no-rep....com` | placeholder | NO | YES |
| `trader_app/services/runtime.py` | private_url | `http:/...host` | local/private deployment URL | YES | NO |
| `migrations/versions/0001_database_foundation.py` | phone | `2026-06-23` | possible personal phone | YES | NO |
| `migrations/versions/0002_spot_futures_preferences.py` | phone | `2026-06-23` | possible personal phone | YES | NO |
| `migrations/versions/0004_payments_foundation.py` | phone | `2026-06-23` | possible personal phone | YES | NO |
| `migrations/versions/0005_performance_indexes.py` | phone | `2026-06-23` | possible personal phone | YES | NO |
| `static/brand/favicon.svg` | phone | `0 0 64 64` | possible personal phone | YES | NO |
| `static/brand/favicon.svg` | phone | `23 7 4...3 15` | possible personal phone | YES | NO |
| `static/brand/favicon.svg` | phone | `42 58 ...2 49` | possible personal phone | YES | NO |
| `static/brand/nexora-logo.svg` | phone | `0 0 720 180` | possible personal phone | YES | NO |
| `static/brand/nexora-logo.svg` | phone | `0 0 0 ...55 0` | possible personal phone | YES | NO |
| `static/brand/nexora-logo.svg` | phone | `44 1 9...0 16` | possible personal phone | YES | NO |
| `static/brand/nexora-logo.svg` | phone | `27 26-...11 7` | possible personal phone | YES | NO |
| `static/proof/proof-1.jpg` | phone | `000...00` | possible personal phone | YES | NO |
| `static/proof/proof-1.jpg` | phone | `888888...8888` | possible personal phone | YES | NO |
| `static/proof/proof-1.jpg` | phone | `999999...9999` | possible personal phone | YES | NO |
| `static/proof/proof-2.jpg` | phone | `000...00` | possible personal phone | YES | NO |
| `static/proof/proof-2.jpg` | phone | `0000000` | possible personal phone | YES | NO |
| `static/proof/proof-2.jpg` | phone | `111111111` | possible personal phone | YES | NO |
| `static/proof/proof-3.jpg` | phone | `000...00` | possible personal phone | YES | NO |
| `static/proof/proof-3.jpg` | phone | `00000` | possible personal phone | YES | NO |
| `static/proof/proof-3.jpg` | phone | `111...11` | possible personal phone | YES | NO |
| `static/proof/proof-5.jpg` | phone | `0004000` | possible personal phone | YES | NO |
| `static/proof/proof-5.jpg` | phone | `800...004` | possible personal phone | YES | NO |
| `static/proof/proof-6.jpg` | phone | `000...00` | possible personal phone | YES | NO |
| `static/proof/proof-7.jpg` | phone | `888888...8888` | possible personal phone | YES | NO |
| `static/proof/proof-8.jpg` | phone | `000...00` | possible personal phone | YES | NO |
| `static/proof/proof-9.jpg` | phone | `1001000` | possible personal phone | YES | NO |
| `static/proof/proof-9.jpg` | phone | `0000000` | possible personal phone | YES | NO |
| `static/proof/proof-9.jpg` | phone | `000...00` | possible personal phone | YES | NO |
| `static/proof/proof-9.jpg` | phone | `000...004` | possible personal phone | YES | NO |
| `static/proof/proof-9.jpg` | phone | `000...01` | possible personal phone | YES | NO |
| `static/proof/proof-9.jpg` | phone | `111111...1111` | possible personal phone | YES | NO |
| `static/proof/proof-9.jpg` | phone | `555555555558` | possible personal phone | YES | NO |

## Sale Package Handling

- `.env` and env backups are excluded.
- `.env.example` is sanitized inside the sale copy with buyer placeholders.
- Personal screenshots, receipts, logs, local DB files, caches, and review diffs are excluded.
- Any detected possible secret is either excluded or replaced with a placeholder in the sale copy.
