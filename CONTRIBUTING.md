# Contributing

Dùng project Docker riêng khi chạy các tình huống ghi/xóa dữ liệu thử nghiệm. Không chạy `tests.scenarios` trên nguồn dùng chung.

Trước khi gửi thay đổi, chạy unit/integration và dashboard checks theo README. Với thay đổi ETL, chạy smoke test từ volume trống. Mô tả hành vi trước/sau và kết quả kiểm tra trong pull request; ghi rõ phần chưa chạy. Không đưa credential, dữ liệu thật hoặc artifacts runtime vào commit.
