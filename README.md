# Megumi Radio

**สถานีวิทยุเว็บ** สำหรับข่าวเช้าสั้นๆ เรื่องอนิเมะ เกม และวัฒนธรรมป๊อป — ภาษาไทยและอังกฤษ

สร้างจากเทมเพลต [myradio](https://github.com/monoradio102/myradio) เปิดด้วย GitHub Pages ไม่ต้องมีเซิร์ฟเวอร์

<p align="center">
  <a href="https://momoyuki.github.io/megumi-radio/"><img src="https://img.shields.io/badge/%E2%96%B6%20ON%20AIR-Megumi%20Radio-ffd028?style=for-the-badge&labelColor=ff4468" alt="Megumi Radio"></a>
</p>

## สถานะตอนนี้

- ตั้งชื่อสถานี / ภาษา / ตารางแล้ว
- ยังไม่มีตอนออกอากาศ (สคริปต์ + เสียงรอบถัดไป)
- ตัวละครยังใช้ชุดจากเทมเพลตชั่วคราว จะเปลี่ยนทีหลัง

## โครงไฟล์หลัก

```
station.json         ข้อมูลสถานี
index.html           เครื่องเล่น
episodes.json        รายการตอน (ว่างอยู่)
episodes/            สคริปต์แต่ละตอน
audio/               ไฟล์เสียง (ไม่ commit เข้า main)
character/           แคสเตอร์
logo.svg             โลโก้
tools/publish.sh     เผยแพร่ขึ้น GitHub Pages
```

## เปิดออกอากาศ

1. เขียนตอนใน `episodes/` ตาม [docs/formats.md](docs/formats.md)
2. สร้างเสียงใส่ `audio/<วันที่>-th.mp3` (และ `-en` ถ้ามี)
3. รัน `tools/publish.sh` แล้วตั้ง Pages ให้ชี้ `gh-pages`

รายละเอียดสำหรับ AI ที่ช่วยรันสถานี: [AGENTS.md](AGENTS.md)

## License

- โปรแกรม (`index.html`, `tools/`): MIT (จาก myradio)
- สคริปต์ของสถานีนี้: CC0
- ตัวละครใน `character/` ตอนนี้ยังเป็นของเทมเพลต — ใช้ได้ตามเงื่อนไข myradio จนกว่าจะเปลี่ยน
- ชื่อสถานี **Megumi Radio** และโลโก้ใน repo นี้เป็นของสถานีนี้
