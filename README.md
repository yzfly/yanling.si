# 言灵 · yanling.si

言灵，是**云中江树**的个人项目。

「言」是说话，「灵」是灵性。这个项目关心的是：如何让 AI 把话说好——把好的沟通经验，沉淀成会倾听、会表达、能替人打电话和聊业务的数字员工。

- 作者：云中江树
- 始于：2026 年 9 月
- 网站：<https://yanling.si>

## 这个仓库是什么

这里只放言灵的公开介绍页（`site/`）和使用记录（`evidence/`），不含任何代码。

`evidence/` 每月自动更新一次：

- 对 <https://yanling.si> 等页面的存档快照与 SHA-256 摘要；
- 互联网档案馆（web.archive.org）的存档链接；
- 摘要文件的 [OpenTimestamps](https://opentimestamps.org/) 时间证明（`.ots`，锚定在比特币区块链上，可独立验证）。

验证某次记录：

```bash
pip install opentimestamps-client
ots verify evidence/2026-10-05/snapshot-sha256.txt.ots   # 目录名是存证日期
```

© 2026 云中江树
