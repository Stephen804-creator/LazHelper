import pytest
from app import config
from app.scanner import safe_workspace_path,safe_file_path,UnsafePath,scan_folder
from app.ai_engine import safe_filename,safe_category
def test_traversal_rejected(tmp_path,monkeypatch):
 root=tmp_path/"workspace";root.mkdir();monkeypatch.setattr(config,"ALLOWED_ROOT",root)
 with pytest.raises(UnsafePath): safe_workspace_path("../outside")
def test_file_inside_workspace(tmp_path,monkeypatch):
 root=tmp_path/"workspace";root.mkdir();(root/"notes.txt").write_text("hello")
 monkeypatch.setattr(config,"ALLOWED_ROOT",root)
 assert safe_file_path("notes.txt")==root/"notes.txt"
 with pytest.raises(UnsafePath): safe_file_path("../notes.txt")
def test_scan_is_read_only(tmp_path,monkeypatch):
 root=tmp_path/"workspace";root.mkdir();f=root/"notes.txt";f.write_text("leave unchanged");before=f.read_bytes()
 monkeypatch.setattr(config,"ALLOWED_ROOT",root);result=scan_folder(".")
 assert result["total_files"]==1 and f.read_bytes()==before
def test_filename_sanitisation_preserves_extension():
 assert safe_filename("../../Quarterly report.exe","accounts.xlsx")=="Quarterly report.xlsx"
 assert "/" not in safe_filename("folder/notes","notes.txt")
def test_category_is_plain_text():
 assert safe_category("../../Finance/Payroll")=="FinancePayroll"
