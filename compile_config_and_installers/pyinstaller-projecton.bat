@"..\win_venv\Scripts\pyinstaller.exe" ^
--noconfirm --clean --noconsole ^
--paths "../src" ^
--hidden-import=PyQt5.sip ^
--distpath C:\Users\pasto\Desktop\output ^
--workpath C:\Users\pasto\Desktop\output\work ^
-i "../src/resources/branding/logo.ico" ^
--exclude-module PyQt5.QtQuick ^
--exclude-module PyQt5.QtQml ^
--exclude-module PyQt5.QtNetwork ^
--exclude-module PyQt5.QtSql ^
--add-data "../src/resources;resources" ^
--add-data "../src/core/static;core/static" ^
--add-data "../src/README.html;." ^
--add-data "../src/README.md;." ^
../src/__main__.py ^
--name="ProjectOn"
@pause