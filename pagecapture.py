#!/usr/bin/env python3
"""PageCapture: auto-scroll a webpage, capture screenshots, and create one PDF.

Install: pip install PySide6 PySide6-WebEngine
Run:     python pagecapture.py
"""
import os
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QImage, QPainter, QPdfWriter, QPageSize, QPageLayout
from PySide6.QtWidgets import (QApplication, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox,
    QVBoxLayout, QWidget)
from PySide6.QtWebEngineWidgets import QWebEngineView

APP = "PageCapture"
DEFAULT_PDF = str(Path.home() / "Documents" / "pagecapture.pdf")

class Window(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle(APP); self.resize(1250, 850)
        self.images=[]; self.positions=[]; self.running=False; self.waiting=False
        self.current_y=0; self.page_h=0; self.view_h=0; self.step=0
        self.web=QWebEngineView(); self.web.loadFinished.connect(self.loaded)
        self.build_ui(); self.statusBar().showMessage("Ready"); self.log("Ready.")

    def build_ui(self):
        root=QVBoxLayout(); top=QHBoxLayout(); self.url=QLineEdit(); self.url.setPlaceholderText("https://... or local HTML file")
        b=QPushButton("Load Page"); b.clicked.connect(self.load); bh=QPushButton("Browse HTML"); bh.clicked.connect(self.browse_html)
        top.addWidget(QLabel("Page:")); top.addWidget(self.url,1); top.addWidget(b); top.addWidget(bh); root.addLayout(top); root.addWidget(self.web,1)
        box=QGroupBox("Capture Settings"); form=QFormLayout(box)
        self.step_pct=QSpinBox(); self.step_pct.setRange(25,100); self.step_pct.setValue(90); self.step_pct.setSuffix(" %")
        self.delay=QDoubleSpinBox(); self.delay.setRange(.2,30); self.delay.setSingleStep(.1); self.delay.setValue(1); self.delay.setSuffix(" sec")
        self.maximum=QSpinBox(); self.maximum.setRange(1,9999); self.maximum.setValue(500)
        self.output=QLineEdit(DEFAULT_PDF); ob=QPushButton("Browse"); ob.clicked.connect(self.browse_output); orow=QHBoxLayout(); orow.addWidget(self.output,1); orow.addWidget(ob)
        self.save_images=QCheckBox("Save individual screenshots"); self.save_images.setChecked(True)
        self.pdf_size=QComboBox(); self.pdf_size.addItems(["A4 portrait","A4 landscape","Letter portrait","Letter landscape"])
        form.addRow("Scroll step:",self.step_pct); form.addRow("Delay after scroll:",self.delay); form.addRow("Maximum captures:",self.maximum); form.addRow("PDF output:",orow); form.addRow("PDF page size:",self.pdf_size); form.addRow("",self.save_images); root.addWidget(box)
        ctl=QHBoxLayout(); self.start=QPushButton("▶ Start Capture"); self.start.clicked.connect(self.start_capture); self.pause=QPushButton("⏸ Pause"); self.pause.clicked.connect(self.pause_capture); self.pause.setEnabled(False); self.stop=QPushButton("■ Stop"); self.stop.clicked.connect(self.stop_capture); self.stop.setEnabled(False); self.pdf=QPushButton("Create PDF"); self.pdf.clicked.connect(self.create_pdf); self.pdf.setEnabled(False); clear=QPushButton("Clear Captures"); clear.clicked.connect(self.clear)
        for w in (self.start,self.pause,self.stop): ctl.addWidget(w)
        ctl.addStretch(); ctl.addWidget(self.pdf); ctl.addWidget(clear); root.addLayout(ctl)
        stat=QHBoxLayout(); self.progress=QProgressBar(); self.count=QLabel("Captures: 0"); self.pos=QLabel("Position: —"); stat.addWidget(self.progress,1); stat.addWidget(self.count); stat.addWidget(self.pos); root.addLayout(stat)
        self.logbox=QPlainTextEdit(); self.logbox.setReadOnly(True); self.logbox.setMaximumHeight(120); root.addWidget(self.logbox)
        self.setCentralWidget(QWidget()); self.centralWidget().setLayout(root); self.menu()

    def menu(self):
        fm=self.menuBar().addMenu("&File"); a=QAction("Load Page",self); a.triggered.connect(self.load); fm.addAction(a); a=QAction("Create PDF",self); a.triggered.connect(self.create_pdf); fm.addAction(a); fm.addSeparator(); a=QAction("Exit",self); a.triggered.connect(self.close); fm.addAction(a)
        hm=self.menuBar().addMenu("&Help"); a=QAction("About",self); a.triggered.connect(self.about); hm.addAction(a)

    def log(self,s): self.logbox.appendPlainText(s)
    def browse_html(self):
        p,_=QFileDialog.getOpenFileName(self,"Open HTML",str(Path.home()),"HTML files (*.html *.htm);;All files (*)")
        if p: self.url.setText(p); self.load()
    def load(self):
        src=self.url.text().strip()
        if not src: QMessageBox.warning(self,APP,"Enter a URL or choose an HTML file."); return
        self.stop_capture(); self.clear()
        if os.path.isfile(src): u=QUrl.fromLocalFile(os.path.abspath(src))
        else:
            if not src.startswith(("http://","https://","file://")): src="https://"+src
            u=QUrl(src)
        self.statusBar().showMessage("Loading..."); self.web.load(u)
    def loaded(self,ok): self.log("Page loaded." if ok else "Page failed to load."); self.statusBar().showMessage("Page loaded." if ok else "Load failed.")

    def metrics(self,cb):
        js="""(()=>{const r=document.documentElement,b=document.body;return {y:Math.round(window.scrollY||0),v:Math.round(window.innerHeight||r.clientHeight||0),h:Math.max(r.scrollHeight,r.offsetHeight,b?b.scrollHeight:0,b?b.offsetHeight:0)}})()"""
        self.web.page().runJavaScript(js,cb)
    def scroll(self,y,cb=None): self.web.page().runJavaScript(f"window.scrollTo(0,{int(y)});",cb or (lambda _:None))

    def start_capture(self):
        if self.running: return
        if self.web.url().isEmpty(): QMessageBox.warning(self,APP,"Load a page first."); return
        self.images=[]; self.positions=[]; self.running=True; self.waiting=True; self.current_y=0
        self.start.setEnabled(False); self.pause.setEnabled(True); self.stop.setEnabled(True); self.pdf.setEnabled(False); self.progress.setValue(0)
        self.log("Preparing page metrics..."); self.scroll(0,lambda _:self.metrics(self.begin))
    def begin(self,m):
        if not self.running: return
        try: self.view_h=int(m["v"]); self.page_h=int(m["h"])
        except Exception: return self.finish("Could not read page dimensions.")
        if self.view_h<=0 or self.page_h<=0: return self.finish("Invalid page dimensions.")
        self.step=max(1,int(self.view_h*self.step_pct.value()/100)); self.waiting=False
        self.log(f"Page {self.page_h}px; viewport {self.view_h}px; step {self.step}px."); QTimer.singleShot(int(self.delay.value()*1000),self.capture)
    def capture(self):
        if not self.running or self.waiting: return
        self.waiting=True; pm=self.web.grab(); im=pm.toImage().convertToFormat(QImage.Format_RGB32)
        if im.isNull(): return self.finish("Screenshot failed.")
        self.images.append(im); self.positions.append(self.current_y); n=len(self.images); self.count.setText(f"Captures: {n}")
        maxy=max(0,self.page_h-self.view_h); self.progress.setValue(100 if maxy==0 else int(min(100,self.current_y*100/maxy))); self.pos.setText(f"Position: {self.current_y}px"); self.log(f"Captured #{n} at {self.current_y}px.")
        if n>=self.maximum.value() or self.current_y>=maxy: self.progress.setValue(100); return self.finish("Reached end of page." if self.current_y>=maxy else "Maximum captures reached.")
        ny=min(maxy,self.current_y+self.step)
        if ny<=self.current_y: return self.finish("Reached end of page.")
        self.current_y=ny; self.scroll(ny,lambda _:QTimer.singleShot(int(self.delay.value()*1000),self.ready))
    def ready(self): self.waiting=False; self.capture()
    def pause_capture(self):
        if self.running: self.running=False; self.waiting=False; self.pause.setEnabled(False); self.start.setEnabled(True); self.log("Paused."); self.statusBar().showMessage("Paused")
    def stop_capture(self):
        self.running=False; self.waiting=False; self.pause.setEnabled(False); self.start.setEnabled(True); self.stop.setEnabled(False); self.pdf.setEnabled(bool(self.images))
    def finish(self,msg):
        self.running=False; self.waiting=False; self.pause.setEnabled(False); self.start.setEnabled(True); self.stop.setEnabled(False); self.pdf.setEnabled(bool(self.images)); self.statusBar().showMessage(msg); self.log(f"{msg} Screenshots: {len(self.images)}")
        if self.save_images.isChecked() and self.images: self.save_pngs()
    def clear(self):
        self.images=[]; self.positions=[]; self.count.setText("Captures: 0"); self.pos.setText("Position: —"); self.progress.setValue(0); self.pdf.setEnabled(False)
    def save_pngs(self):
        p=Path(self.output.text().strip() or DEFAULT_PDF); d=p.parent/(p.stem+"_screenshots"); d.mkdir(parents=True,exist_ok=True)
        for i,im in enumerate(self.images,1): im.save(str(d/f"page_{i:04d}.png"),"PNG")
        self.log(f"Screenshots saved: {d}")

    def browse_output(self):
        p,_=QFileDialog.getSaveFileName(self,"PDF output",self.output.text() or DEFAULT_PDF,"PDF files (*.pdf)")
        if p: self.output.setText(p if p.lower().endswith('.pdf') else p+'.pdf')
    def layout_for_size(self):
        text=self.pdf_size.currentText(); landscape="landscape" in text; size=QPageSize.Letter if "Letter" in text else QPageSize.A4; orient=QPageLayout.Landscape if landscape else QPageLayout.Portrait; return QPageLayout(size,orient)
    def create_pdf(self):
        if not self.images: QMessageBox.information(self,APP,"No screenshots to export."); return
        p=Path(self.output.text().strip() or DEFAULT_PDF); p.parent.mkdir(parents=True,exist_ok=True)
        try:
            writer=QPdfWriter(str(p)); writer.setResolution(96); writer.setPageLayout(self.layout_for_size()); rect=writer.pageLayout().paintRectPixels(writer.resolution())
            for i,im in enumerate(self.images):
                painter=QPainter(writer); painter.setRenderHint(QPainter.SmoothPixmapTransform); scale=min(rect.width()/im.width(),rect.height()/im.height()); w=int(im.width()*scale); h=int(im.height()*scale); x=rect.x()+(rect.width()-w)//2; y=rect.y()+(rect.height()-h)//2; painter.drawImage(x,y,im.scaled(w,h,Qt.KeepAspectRatio,Qt.SmoothTransformation)); painter.end()
                if i<len(self.images)-1: writer.newPage()
            writer.close(); self.log(f"PDF created: {p}"); self.statusBar().showMessage(f"PDF created: {p}"); QMessageBox.information(self,APP,f"PDF created successfully.\n\n{p}\n\n{len(self.images)} screenshots combined.")
        except Exception as e: QMessageBox.critical(self,APP,f"PDF creation failed:\n\n{e}")
    def about(self): QMessageBox.about(self,APP,"<h2>PageCapture</h2><p>Auto-scrolls a webpage, captures the visible page, and combines the captures into one PDF.</p><p>Single-file PySide6 utility.</p>")

def main():
    app=QApplication(sys.argv); app.setApplicationName(APP); w=Window(); w.show(); sys.exit(app.exec())
if __name__=='__main__': main()
