@"..\win_venv\Scripts\pyinstaller.exe" ^
--noconfirm --clean --noconsole ^
--paths "../src" ^
--hidden-import=PyQt5.sip ^
--distpath C:\Users\pasto\Desktop\output ^
--workpath C:\Users\pasto\Desktop\output\work ^
-i "../src/resources/branding/logo.ico" ^
--add-data "../src/resources;resources" ^
--add-data "../src/core/static;core/static" ^
../src/__main__.py ^
--name="ProjectOn"
@pause