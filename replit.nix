{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.python311Packages.flask
    pkgs.python311Packages.pillow
    pkgs.python311Packages.pytesseract
    pkgs.python311Packages.img2pdf
    pkgs.python311Packages.PyMuPDF
    pkgs.tesseract4
  ];
}
