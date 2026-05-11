@"..\win_venv\Scripts\pyinstaller.exe" ^
	--noconfirm ^
	--clean ^
	--noconsole ^
	-i "../src/resources/branding/logo.ico" ^
	--paths "../src" ^
	--exclude-module PyQt5.QtQuick ^
	--add-data "../src/resources;resources" ^
	--add-data "../src/core/static;core/static" ^
	--add-data "../src/README.html;." ^
	--add-data "../src/README.md;." ^
	--hidden-import=PyQt5.sip ^
	--distpath C:\Users\pasto\Desktop\output ^
	--workpath C:\Users\pasto\Desktop\output\work ^
	--name="ProjectOn" ^
	../src/__main__.py
@pause