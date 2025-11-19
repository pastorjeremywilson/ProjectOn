import subprocess

import wmi
from PyQt6.QtGui import QImage, QPixmap, QIcon
from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel, QPushButton, QHBoxLayout, QComboBox, QDialog
from pymupdf import pymupdf


class PrintDialog(QDialog):
    """
    Class implementing QDialog to show the user a print dialog, also showing a preview of the item to be printed.
    :param str pdf_file: the path to a pdf file to print
    :param GUI gui: the current instance of a gui
    :param boolean landscape: optional: whether the pdf is to be printed in landscape orientation
    """
    def __init__(self, pdf_file, gui, landscape=False):
        """
        Class implementing QDialog to show the user a print dialog, also showing a preview of the item to be printed.
        :param str pdf_file: the path to a pdf file to print
        :param GUI gui: the current instance of a gui
        :param boolean landscape: optional: whether the pdf is to be printed in landscape orientation
        """
        super().__init__()
        self.gui = gui
        self.landscape = landscape
        self.pdf_file = pdf_file

        self.pdf = pymupdf.open(self.pdf_file)
        self.num_pages = len(self.pdf)
        self.pages = []
        self.current_page = 0

        self.layout = QGridLayout()
        self.layout.setRowStretch(0, 1)
        self.layout.setRowStretch(1, 1)
        self.layout.setRowStretch(2, 1)
        self.layout.setRowStretch(3, 100)
        self.layout.setRowStretch(4, 1)

        self.setLayout(self.layout)
        self.setWindowTitle('Print')
        self.setGeometry(50, 50, 100, 100)
        self.get_pages()
        self.init_components()

    def init_components(self):
        """
        Creates the widgets to be shown in the dialog
        """
        self.preview_label = QLabel('Preview:')
        self.preview_label.setFont(self.gui.bold_font)
        self.layout.addWidget(self.preview_label, 0, 0)

        self.pdf_label = QLabel()
        self.pdf_label.setPixmap(self.pages[0])
        self.pdf_label.setFixedSize(self.pages[0].size())
        self.layout.addWidget(self.pdf_label, 1, 0, 3, 1)

        nav_button_widget = QWidget()
        nav_button_layout = QHBoxLayout()
        nav_button_widget.setLayout(nav_button_layout)

        previous_button = QPushButton()
        previous_button.setIcon(QIcon('resources/gui_icons/previous.svg'))
        previous_button.setAutoFillBackground(False)
        previous_button.setStyleSheet('border: none')
        previous_button.clicked.connect(self.previous_page)
        nav_button_layout.addStretch()
        nav_button_layout.addWidget(previous_button)
        nav_button_layout.addSpacing(20)

        self.page_label = QLabel('Page 1 of ' + str(self.num_pages))
        self.page_label.setFont(self.gui.bold_font)
        nav_button_layout.addWidget(self.page_label)
        nav_button_layout.addSpacing(20)

        next_button = QPushButton()
        next_button.setIcon(QIcon('resources/gui_icons/next.svg'))
        next_button.setAutoFillBackground(False)
        next_button.setStyleSheet('border: none')
        next_button.clicked.connect(self.next_page)
        nav_button_layout.addWidget(next_button)
        nav_button_layout.addStretch()

        self.layout.addWidget(nav_button_widget, 4, 0)

        printer_label = QLabel('Send to:')
        printer_label.setFont(self.gui.bold_font)
        self.layout.addWidget(printer_label, 0, 1)

        printer_combobox = self.get_printers()
        printer_combobox.setFont(self.gui.standard_font)
        self.layout.addWidget(printer_combobox, 1, 1)

        ok_cancel_buttons = QWidget()
        ok_cancel_layout = QHBoxLayout()
        ok_cancel_buttons.setLayout(ok_cancel_layout)

        ok_button = QPushButton('Print')
        ok_button.setFont(self.gui.standard_font)
        ok_button.clicked.connect(lambda: self.do_print(printer_combobox.currentText()))
        ok_cancel_layout.addStretch()
        ok_cancel_layout.addWidget(ok_button)
        ok_cancel_layout.addSpacing(20)

        cancel_button = QPushButton('Cancel')
        cancel_button.setFont(self.gui.standard_font)
        cancel_button.clicked.connect(self.cancel)
        ok_cancel_layout.addWidget(cancel_button)
        ok_cancel_layout.addStretch()

        self.layout.addWidget(ok_cancel_buttons, 2, 1)

    def get_printers(self):
        """
        Obtain a list of printers currently installed on the system
        """
        win_management = wmi.WMI()
        printers = win_management.Win32_Printer()

        printer_combobox = QComboBox()
        default = ''
        for printer in printers:
            if not printer.Hidden:
                printer_combobox.addItem(printer.Name)
            if printer.Default:
                default = printer.Name

        printer_combobox.setCurrentText(default)
        return printer_combobox

    def get_pages(self):
        """
        Gets the individual pages of the pdf file and converts each to a QPixmap
        """
        for page in self.pdf:
            pixmap = page.get_pixmap()

            fmt = QImage.Format.Format_RGBA8888 if pixmap.alpha else QImage.Format.Format_RGB888
            q_pixmap = QPixmap.fromImage(QImage(pixmap.samples_ptr, pixmap.width, pixmap.height, fmt))

            self.pages.append(q_pixmap)

    def previous_page(self):
        """
        Method to show the previous page in the PDF file upon user input
        """
        if not self.current_page == 0:
            self.current_page -= 1
            self.page_label.setText('Page ' + str(self.current_page + 1) + ' of ' + str(self.num_pages))
            self.pdf_label.setPixmap(self.pages[self.current_page])

    def next_page(self):
        """
        Method to show the next page in the PDF file upon user input
        """
        if not self.current_page == self.num_pages - 1:
            self.current_page += 1
            self.page_label.setText('Page ' + str(self.current_page + 1) + ' of ' + str(self.num_pages))
            self.pdf_label.setPixmap(self.pages[self.current_page])

    def do_print(self, printer):
        """
        Method to perform the printing function using ghostscript
        :param str printer: the name of the user's chosen printer
        """
        print('Opening print subprocess')
        CREATE_NO_WINDOW = 0x08000000
        if self.landscape:
            command = [
                    'ghostscript/gsprint.exe',
                    '-sDEVICE=mswinpr2',
                    '-sOutputFile="%printer%' + printer + '"',
                    '-landscape',
                    self.pdf_file,
                    '-ghostscript',
                    'ghostscript/gswin64c.exe'
            ]
        else:
            command = [
                'ghostscript/gsprint.exe',
                '-sDEVICE=mswinpr2',
                '-sOutputFile="%printer%' + printer + '"',
                self.pdf_file,
                '-ghostscript',
                'ghostscript/gswin64c.exe'
            ]

        p = subprocess.Popen(
            command,
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        print('Capturing print subprocess sdtout & stderr')
        stdout, stderr = p.communicate()
        print(stdout, stderr)
        self.done(0)

    def cancel(self):
        """
        Method to end the QDialog upon user clicking the "Cancel" button
        """
        self.done(0)

    def closeEvent(self, evt):
        self.done(0)
