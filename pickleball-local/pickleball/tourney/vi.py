"""Vietnamese translations for every tr() string in the app.

Keys are the English source text exactly as written in the code; values keep
the same {placeholders}. tests/test_i18n.py fails if any string the app can
show is missing here — run `python -m tourney.i18n_catalog` to list them.

Terms used throughout: trận (match), ván (game), pha bóng (rally), giao bóng
(serve), đổi giao bóng (side out), hội ý (timeout), đổi sân (switch ends),
bảng (pool), hạt giống (seed), sơ đồ thi đấu (draw), nhánh đấu (bracket),
đội/VĐV (entry), xử thắng (walkover), miễn đấu (bye).
"""

VI: dict[str, str] = {
    # --- small words & fragments -------------------------------------------
    "  (withdrawn)": "  (đã rút lui)",
    " (free)": " (trống)",
    " (in use)": " (đang dùng)",
    " on {court}": " tại {court}",
    " · {n} unassigned": " · {n} chưa xếp bảng",
    " · {n} unplaced": " · {n} chưa xếp",
    " — {who} scoring": " — {who} đang tính điểm",
    "vs": "gặp",
    "TBD": "Chưa xác định",
    "Court TBD": "Chưa có sân",
    "court TBD": "chưa có sân",
    "empty": "trống",
    "— empty —": "— để trống —",
    "— not set —": "— chưa chọn —",
    "bye": "miễn đấu",
    "walkover": "xử thắng",
    "live": "đang đấu",
    "left": "trái",
    "right": "phải",
    "decider": "ván quyết định",
    "on court": "đang thi đấu",
    "another event": "nội dung khác",
    "no court free": "không còn sân trống",
    "an entry would face itself": "một đội sẽ phải gặp chính mình",
    "gender not set": "chưa có giới tính",
    "needs {g}": "cần {g}",
    "Optional": "Không bắt buộc",
    "No": "Không",
    "Male": "Nam",
    "Female": "Nữ",
    "Another admin": "Một quản trị viên khác",
    "The next match": "Trận tiếp theo",
    "G{n}": "V{n}",
    "M{n}": "T{n}",
    "Match {n}": "Trận {n}",
    "Game {n}": "Ván {n}",
    "Side {s}": "Bên {s}",
    "Side": "Bên",
    "Side A": "Bên A",
    "Side B": "Bên B",
    "server {n}": "người giao {n}",
    "best of {n}": "thắng {n} ván (BO{n})",
    "Best of {n}": "Đấu {n} ván (BO{n})",
    "{n}s ago": "{n} giây trước",
    "{n}m ago": "{n} phút trước",
    "{n}h ago": "{n} giờ trước",
    "{n}d ago": "{n} ngày trước",

    # --- statuses ----------------------------------------------------------
    "Setting up": "Đang chuẩn bị",
    "In progress": "Đang diễn ra",
    "Complete": "Đã kết thúc",
    "Pending": "Chưa đấu",
    "Live": "Trực tiếp",
    "Done": "Đã xong",
    "Walkover": "Xử thắng",
    "Void": "Hủy",
    "Active": "Đang thi đấu",
    "Withdrawn": "Đã rút lui",
    "Open": "Mở",
    "Closed": "Đóng",
    "Free": "Trống",

    # --- round names -------------------------------------------------------
    "Final": "Chung kết",
    "Semifinal": "Bán kết",
    "Quarterfinal": "Tứ kết",
    "3rd place": "Tranh hạng ba",
    "Grand Final": "Chung kết tổng",
    "Grand Final (reset)": "Chung kết tổng (trận quyết định)",
    "WB Final": "Chung kết nhánh thắng",
    "LB Final": "Chung kết nhánh thua",
    "Quick Match": "Trận đấu nhanh",
    "Round {n}": "Vòng {n}",
    "Round of {n}": "Vòng {n} đội",
    "Pool {pool} · Round {n}": "Bảng {pool} · Vòng {n}",
    "Losers bracket · Round {n}": "Nhánh thua · Vòng {n}",
    "Winners bracket · {label}": "Nhánh thắng · {label}",
    "Playoff · {label}": "Loại trực tiếp · {label}",
    "Winners bracket": "Nhánh thắng",
    "Losers bracket": "Nhánh thua",
    "Grand final": "Chung kết tổng",
    "Playoffs": "Vòng loại trực tiếp",

    # --- categories / formats / scoring -----------------------------------
    "Everyone plays everyone once. Best for 4–10 entries.":
        "Mỗi đội gặp tất cả các đội khác một lần. Phù hợp cho 4–10 đội.",
    "Fixed number of rounds, paired by record each round, no eliminations.":
        "Số vòng cố định, mỗi vòng ghép cặp theo thành tích, không bị loại.",
    "Lose once and you're out. Fastest format.":
        "Thua một trận là bị loại. Thể thức nhanh nhất.",
    "Losers drop to a consolation bracket and can still win.":
        "Đội thua xuống nhánh thua và vẫn có thể vô địch.",
    "Round robin pools first, top finishers advance to a knockout bracket.":
        "Đấu vòng tròn chia bảng trước, các đội đứng đầu vào vòng loại trực tiếp.",
    "To 11 (first to 11 wins, no win-by-2)": "Đến 11 (ai chạm 11 trước thắng, không cần cách 2)",
    "To 11, win by 2": "Đến 11, thắng cách 2 điểm",
    "To 11, win by 2, cap 15": "Đến 11, thắng cách 2, tối đa 15",
    "To 15 (first to 15 wins, no win-by-2)": "Đến 15 (ai chạm 15 trước thắng, không cần cách 2)",
    "To 15, win by 2": "Đến 15, thắng cách 2 điểm",
    "To 15, win by 2, cap 21": "Đến 15, thắng cách 2, tối đa 21",
    "To 21, win by 2": "Đến 21, thắng cách 2 điểm",
    "Side-out scoring (only the serving side scores)":
        "Tính điểm giao bóng (chỉ bên giao bóng được điểm)",
    "Rally scoring (a point on every rally)": "Tính điểm mỗi pha bóng (rally)",
    "Side-out": "Tính điểm giao bóng",
    "Rally scoring": "Tính điểm mỗi pha",
    "Side-out is the traditional USA Pickleball game: only the serving side scores, two servers "
    "per side, 0-0-2 start. Rally scoring gives a point on every rally.":
        "Tính điểm giao bóng là luật truyền thống của USA Pickleball: chỉ bên giao bóng được "
        "điểm, mỗi bên có hai người giao, bắt đầu 0-0-2. Tính điểm mỗi pha: pha nào cũng có điểm.",

    # --- themes ------------------------------------------------------------
    "Stay Liquid — ocean & gold": "Stay Liquid — đại dương & vàng",
    "Tribal — ivory & terracotta": "Tribal — ngà & đất nung",
    "Cyberpunk — neon HUD": "Cyberpunk — neon",
    "Minimal — clean & simple": "Minimal — tối giản",

    # --- sidebar / access --------------------------------------------------
    "{e} event(s) · {p} players · {status}": "{e} nội dung · {p} VĐV · {status}",
    "No tournaments yet. Sign in and create one on the Setup page.":
        "Chưa có giải đấu nào. Đăng nhập và tạo giải ở trang Thiết lập.",
    "Default passcodes: admin `{a}`, referee `{r}`. Set your own in `.streamlit/secrets.toml` "
    "before a real event.":
        "Mã mặc định: quản trị `{a}`, trọng tài `{r}`. Hãy đặt mã riêng trong "
        "`.streamlit/secrets.toml` trước khi tổ chức giải thật.",
    "Storage: {x}": "Lưu trữ: {x}",
    "Sign in as an admin in the sidebar to {action}. You can still read everything here.":
        "Đăng nhập quản trị viên ở thanh bên để {action}. Bạn vẫn xem được mọi thông tin ở đây.",
    "Sign in as an admin or referee in the sidebar to {action}. You can still read everything here.":
        "Đăng nhập quản trị viên hoặc trọng tài ở thanh bên để {action}. "
        "Bạn vẫn xem được mọi thông tin ở đây.",
    "make changes": "thay đổi",
    "enter scores": "nhập điểm",
    "create tournaments": "tạo giải đấu",
    "manage players": "quản lý vận động viên",
    "call matches on": "gọi trận vào sân",
    "change fixtures": "sửa lịch thi đấu",
    "start or score a quick match": "bắt đầu hoặc tính điểm trận đấu nhanh",
    "Pick a tournament in the sidebar, or create one on the Setup page.":
        "Chọn giải đấu ở thanh bên, hoặc tạo giải mới ở trang Thiết lập.",
    "Pick a tournament in the sidebar, or start one above.":
        "Chọn giải đấu ở thanh bên, hoặc tạo giải mới ở trên.",
    "That tournament no longer exists.": "Giải đấu này không còn tồn tại.",
    "Event": "Nội dung",
    "All events": "Tất cả nội dung",

    # --- standings tables --------------------------------------------------
    "Entry": "Đội/VĐV",
    "P": "Trận",
    "W": "Thắng",
    "L": "Thua",
    "Win %": "% thắng",
    "Games": "Ván",
    "Pts": "Điểm",
    "Diff": "Hiệu số",
    "Pool": "Bảng",
    "Player": "VĐV",
    "Club": "CLB",
    "Events": "Nội dung",
    "Standings": "Bảng xếp hạng",
    "Draw": "Sơ đồ thi đấu",
    "Champion": "Vô địch",
    "Runner-up": "Á quân",
    "Third": "Hạng ba",
    "Player leaderboard": "Xếp hạng cá nhân",
    "Buchholz is the combined win total of the opponents each entry actually faced — it separates "
    "equal records by strength of schedule.":
        "Buchholz là tổng số trận thắng của các đối thủ mà mỗi đội đã gặp — dùng để phân định "
        "các đội bằng thành tích theo độ khó của lịch đấu.",
    "Ties break on head-to-head first, then game differential, then point differential.":
        "Khi bằng nhau, xét đối đầu trước, rồi hiệu số ván, rồi hiệu số điểm.",
    "Every individual across every event they entered — doubles results count for both partners.":
        "Mỗi VĐV trên tất cả nội dung đã tham gia — kết quả đánh đôi tính cho cả hai người.",

    # --- live board / venue display / match cards -------------------------
    "Live board": "Bảng trực tiếp",
    "Call {call}": "Đọc điểm {call}",
    "No bracket yet.": "Chưa có nhánh đấu.",
    "On court": "Đang thi đấu",
    "Next up": "Sắp thi đấu",
    "Latest results": "Kết quả mới nhất",
    "No matches on court.": "Không có trận nào trên sân.",
    "{n} match(es) waiting on players who are still on court.":
        "{n} trận đang chờ VĐV còn đang thi đấu ở sân khác.",
    "Nothing waiting.": "Không có trận nào đang chờ.",
    "No results yet.": "Chưa có kết quả.",
    "No events yet.": "Chưa có nội dung thi đấu.",
    "Refreshes on its own. Collapse the sidebar and press F11 to cast this to a screen at the courts.":
        "Tự động cập nhật. Thu gọn thanh bên và nhấn F11 để chiếu lên màn hình tại sân.",

    # --- draws & standings page -------------------------------------------
    "Draws and standings": "Sơ đồ thi đấu & Bảng xếp hạng",
    "No entries yet.": "Chưa có đội/VĐV đăng ký.",
    "No draw yet ({n} entries confirmed).": "Chưa có sơ đồ thi đấu ({n} đội/VĐV đã xác nhận).",
    "No draw yet.": "Chưa có sơ đồ thi đấu.",
    "Set up and generate the draw in Players & entries → Event entries.":
        "Thiết lập và tạo sơ đồ thi đấu ở Vận động viên & Đăng ký → Đăng ký theo nội dung.",
    "Pools": "Số bảng",
    "Pool {p}": "Bảng {p}",
    "Pool {p}: {n}": "Bảng {p}: {n}",
    "Playoff bracket appears once every pool match is finished.":
        "Nhánh loại trực tiếp sẽ xuất hiện khi tất cả trận vòng bảng kết thúc.",
    "The losers-bracket survivor won the first grand final, so a deciding match was created — both "
    "sides carry one loss.":
        "Đội từ nhánh thua đã thắng trận chung kết tổng đầu tiên nên có thêm trận quyết định — "
        "hai bên đều đã thua một trận.",

    # --- draw setup --------------------------------------------------------
    "Draw method": "Cách bốc thăm",
    "By seed": "Theo hạt giống",
    "Randomize": "Ngẫu nhiên",
    "Manual (drawn outside the app)": "Thủ công (đã bốc thăm bên ngoài)",
    "Custom (build the bracket by hand)": "Tự xếp (tự dựng nhánh đấu)",
    "Pair up entries into matches, then route each one's winner — and its loser, if you want them "
    "to keep playing too — to an exact slot next round.":
        "Ghép các đội thành trận, sau đó chỉ định đội thắng — và cả đội thua nếu muốn họ đấu "
        "tiếp — vào đúng vị trí ở vòng sau.",
    "R{r} · slot {s}": "V{r} · vị trí {s}",
    "R{r} · Match {m} · slot {s}": "V{r} · Trận {m} · vị trí {s}",
    "More than one match is routed into the same slot ({spots}) — only the most recently saved one "
    "will actually land there. Fix that below.":
        "Có nhiều trận được chỉ định vào cùng một vị trí ({spots}) — chỉ trận lưu sau cùng được "
        "tính. Hãy sửa lại bên dưới.",
    "Add matches to a round": "Thêm trận vào một vòng",
    "Round {next} would be a new round — but you can also add more matches to an existing round "
    "(like round {last}) if you need another slot for, say, a loser who's still playing.":
        "Vòng {next} sẽ là vòng mới — bạn cũng có thể thêm trận vào vòng đã có (như vòng {last}) "
        "nếu cần thêm vị trí, ví dụ cho một đội thua vẫn được đấu tiếp.",
    "Round number": "Số vòng",
    "How many matches to add": "Số trận cần thêm",
    "Add {n} match(es) to round {r}": "Thêm {n} trận vào vòng {r}",
    "Need at least two entries before you can build round 1.":
        "Cần ít nhất hai đội để tạo vòng 1.",
    "{n} entries — one will be left unpaired here; pair up the rest, then give the odd one out a "
    "bye on the Fixtures page afterward.":
        "{n} đội — sẽ có một đội lẻ; hãy ghép cặp các đội còn lại, sau đó cho đội lẻ miễn đấu ở "
        "trang Lịch thi đấu.",
    "Unpaired": "Chưa ghép cặp",
    "Drag two entries into the same match to pair them up.":
        "Kéo hai đội vào cùng một trận để ghép cặp.",
    "{a} of {b} round-1 matches paired up.": "Đã ghép {a}/{b} trận vòng 1.",
    "Create round 1": "Tạo vòng 1",
    "Round 1 created — route each match's winner (and loser, if you want) below, or add round 2 "
    "once you're ready.":
        "Đã tạo vòng 1 — chỉ định đội thắng (và đội thua nếu muốn) của mỗi trận bên dưới, hoặc "
        "thêm vòng 2 khi sẵn sàng.",
    "done — {w} won": "xong — {w} thắng",
    "Add a later round below, then come back here to route this match.":
        "Thêm vòng sau ở bên dưới, rồi quay lại đây để chỉ định cho trận này.",
    "Winner advances to": "Đội thắng vào",
    "Loser advances to": "Đội thua vào",
    "Save routing": "Lưu chỉ định",
    "The draw already happened outside the app — drag each entry into the pool it was drawn into. "
    "Nothing here is computed for you.":
        "Việc bốc thăm đã diễn ra bên ngoài — kéo từng đội vào bảng mà họ đã bốc được. "
        "Ứng dụng không tự tính gì ở đây.",
    "Unassigned": "Chưa xếp bảng",
    "{n} entry(ies) not yet assigned to a pool.": "{n} đội chưa được xếp bảng.",
    "Shuffles every entry into a fresh random order, ignoring any seed numbers — pools are then "
    "filled by snaking down that order.":
        "Xáo trộn ngẫu nhiên thứ tự các đội, bỏ qua hạt giống — sau đó chia bảng theo kiểu "
        "rắn lượn (zig-zag) theo thứ tự đó.",
    "Shuffles every entry into a fresh random order, ignoring any seed numbers.":
        "Xáo trộn ngẫu nhiên thứ tự các đội, bỏ qua hạt giống.",
    "🎲 Shuffle order": "🎲 Xáo trộn thứ tự",
    "The draw already happened outside the app (names pulled from a hat, a printed sheet, etc). Drag "
    "entries into that exact order, then click **Record this order** below — even if the list "
    "already looks right, nothing is saved until you do.":
        "Việc bốc thăm đã diễn ra bên ngoài (bốc thăm giấy, danh sách in sẵn…). Kéo các đội theo "
        "đúng thứ tự đó, rồi bấm **Ghi nhận thứ tự này** bên dưới — kể cả khi danh sách đã đúng, "
        "chưa có gì được lưu cho đến khi bạn bấm.",
    "Entries with a seed are ranked first; anyone else fills the remaining positions at random when "
    "you generate the draw, then pools are filled by snaking down that order.":
        "Đội có hạt giống được xếp trước; các đội còn lại được xếp ngẫu nhiên khi tạo sơ đồ, sau "
        "đó chia bảng theo kiểu rắn lượn (zig-zag) theo thứ tự đó.",
    "Entries with a seed are ranked first; anyone else fills the remaining positions at random when "
    "you generate the draw.":
        "Đội có hạt giống được xếp trước; các đội còn lại được xếp ngẫu nhiên khi tạo sơ đồ.",
    "Drag to set the order — top is position 1.": "Kéo để sắp thứ tự — trên cùng là vị trí số 1.",
    "Nothing recorded yet — the list above is only a preview until you save it, even if the order "
    "already looks correct.":
        "Chưa ghi nhận — danh sách trên chỉ là xem trước cho đến khi bạn lưu, kể cả khi thứ tự "
        "đã đúng.",
    "✅ Record this order": "✅ Ghi nhận thứ tự này",
    "Recorded.": "Đã ghi nhận.",
    "✅ Recorded — every entry has a position.": "✅ Đã ghi nhận — mọi đội đều có vị trí.",

    # --- players & entries -------------------------------------------------
    "Players and entries": "Vận động viên & Đăng ký",
    "Roster": "Danh sách VĐV",
    "Event entries": "Đăng ký theo nội dung",
    "{n} players registered. Names are shared across every event, so the same person can enter "
    "singles and doubles.":
        "{n} VĐV đã đăng ký. Tên dùng chung cho mọi nội dung, nên một người có thể đánh cả đơn "
        "và đôi.",
    "Add one player": "Thêm một VĐV",
    "Name": "Họ tên",
    "Gender": "Giới tính",
    "Add player": "Thêm VĐV",
    "{name} added.": "Đã thêm {name}.",
    "Paste a list": "Dán danh sách",
    "One per line: `Name, M, Club` — gender (M/F) and club optional.":
        "Mỗi dòng một người: `Họ tên, M, CLB` — giới tính (M = nam, F = nữ) và CLB không bắt buộc.",
    "Players": "Danh sách VĐV",
    "Add all": "Thêm tất cả",
    "{n} name(s) processed. Duplicates were merged.": "Đã xử lý {n} tên. Tên trùng đã được gộp.",
    "No players yet.": "Chưa có VĐV nào.",
    "Rating": "Điểm trình độ",
    "Save roster edits": "Lưu thay đổi danh sách",
    "{n} player(s) updated.": "Đã cập nhật {n} VĐV.",
    "Remove a player": "Xóa một VĐV",
    "Remove": "Xóa",
    "Removed.": "Đã xóa.",
    "Add an event on the Setup page first.": "Hãy thêm nội dung thi đấu ở trang Thiết lập trước.",
    "Add players to the roster first.": "Hãy thêm VĐV vào danh sách trước.",
    "This event already has a draw. New entries will not appear in it — clear the draw below if you "
    "need to re-seed.":
        "Nội dung này đã có sơ đồ thi đấu. Đội mới sẽ không có trong sơ đồ — hãy xóa sơ đồ bên "
        "dưới nếu cần xếp lại.",
    "Build entries for {event}": "Tạo danh sách đăng ký cho {event}",
    "{n} player(s) without a gender set do not appear below ({names}{more}) — set their gender on "
    "the Roster tab.":
        "{n} VĐV chưa có giới tính sẽ không hiện bên dưới ({names}{more}) — hãy cập nhật giới "
        "tính ở thẻ Danh sách VĐV.",
    "No eligible unentered players left for this event.":
        "Không còn VĐV hợp lệ nào chưa đăng ký nội dung này.",
    "{n} eligible unentered players available. Team size: {size}.":
        "Còn {n} VĐV hợp lệ chưa đăng ký. Số người mỗi đội: {size}.",
    "Players participating — pick exactly who is in this event":
        "VĐV tham gia — chọn đúng những người thi đấu nội dung này",
    "Choose players": "Chọn VĐV",
    "{n} selected — doesn't divide evenly into teams of {size}. Pick a multiple of {size}.":
        "Đã chọn {n} — không chia đều thành đội {size} người. Hãy chọn bội số của {size}.",
    "Create team zones": "Tạo ô xếp đội",
    "{n} entries": "{n} đội/VĐV",
    "No entries in this event yet.": "Nội dung này chưa có đội/VĐV đăng ký.",
    "Seed": "Hạt giống",
    "Status": "Trạng thái",
    "Save seeds": "Lưu hạt giống",
    "{n} seed(s) updated.": "Đã cập nhật {n} hạt giống.",
    "🔄 Substitute a player": "🔄 Thay người",
    "A last-minute withdrawal — swap one player out for another on an existing team. The team keeps "
    "its seed, its pool, and its exact spot in the draw; only who's playing changes.":
        "Rút lui phút chót — thay một VĐV trong đội bằng người khác. Đội giữ nguyên hạt giống, "
        "bảng và vị trí trong sơ đồ; chỉ thay người thi đấu.",
    "Team": "Đội",
    "Who's leaving": "Người rút ra",
    "No eligible replacement in the roster — add one on the Roster tab first, then come back here.":
        "Không có người thay thế hợp lệ — hãy thêm VĐV ở thẻ Danh sách VĐV rồi quay lại.",
    "Who's coming in": "Người vào thay",
    "Substitute now": "Thay người ngay",
    "Done — now {name}.": "Xong — giờ là {name}.",
    "Withdraw an entry": "Cho đội rút lui",
    "Keeps completed results and concedes everything still to play.":
        "Giữ nguyên kết quả đã đấu, các trận còn lại bị xử thua.",
    "Withdraw": "Rút lui",
    "Withdrawn.": "Đã rút lui.",
    "Delete an entry": "Xóa một đội",
    "Only possible before they have played.": "Chỉ xóa được khi đội chưa thi đấu.",
    "Delete entry": "Xóa đội",
    "Deleted.": "Đã xóa.",
    "All {n} eligible players are in — each becomes its own entry, no need to drag.":
        "Cả {n} VĐV hợp lệ đều tham gia — mỗi người là một suất, không cần kéo thả.",
    "Confirm entries": "Xác nhận đăng ký",
    "{n} entries confirmed.": "Đã xác nhận {n} suất.",
    "Unplaced": "Chưa xếp",
    "Drag a player onto a zone to place them — {n} zone(s) of {size}.":
        "Kéo VĐV vào ô để xếp — {n} ô, mỗi ô {size} người.",
    "{zone}: needs exactly {size}, has {n}": "{zone}: cần đúng {size}, đang có {n}",
    "{a} of {b} complete": "Hoàn tất {a}/{b}",
    "{n} entry(ies) confirmed.": "Đã xác nhận {n} đội.",
    "Set up the draw for {event}": "Thiết lập sơ đồ thi đấu cho {event}",
    "Add at least two entries above before building the draw.":
        "Hãy thêm ít nhất hai đội ở trên trước khi tạo sơ đồ.",
    "Not every entry has a pool yet — drag them into pools above.":
        "Chưa phải đội nào cũng có bảng — hãy kéo vào bảng ở trên.",
    "Include a 3rd place match": "Có trận tranh hạng ba",
    "Generate draw": "Tạo sơ đồ thi đấu",
    "Draw created.": "Đã tạo sơ đồ thi đấu.",
    "{a} of {b} matches played": "Đã đấu {a}/{b} trận",
    "Draw method: {m}. Enter results on the Scoring desk page; the bracket is on Draws & standings.":
        "Cách bốc thăm: {m}. Nhập kết quả ở Bàn tính điểm; xem nhánh đấu ở Bốc thăm & Bảng xếp hạng.",
    "Continue building the bracket": "Tiếp tục dựng nhánh đấu",
    "Clear draw and start over": "Xóa sơ đồ và làm lại",
    "This deletes every match and score in this event. Entries stay.":
        "Thao tác này xóa mọi trận và điểm của nội dung. Danh sách đội được giữ lại.",
    "Yes, clear it": "Đồng ý, xóa",

    # --- setup -------------------------------------------------------------
    "Setup": "Thiết lập",
    "Tournaments and events": "Giải đấu & Nội dung",
    "Category": "Nội dung",
    "Format": "Thể thức",
    "Game scoring": "Cách tính điểm ván",
    "Match length": "Số ván mỗi trận",
    "Scoring system": "Luật tính điểm",
    "Swiss settings": "Thiết lập hệ Thụy Sĩ",
    "Swiss rounds": "Số vòng Thụy Sĩ",
    "How many rounds are paired before the event ends.": "Số vòng được ghép cặp trước khi kết thúc.",
    "Pool play settings": "Thiết lập vòng bảng",
    "Advance per pool": "Số đội đi tiếp mỗi bảng",
    "How many entries from each pool reach the playoffs.":
        "Số đội ở mỗi bảng được vào vòng loại trực tiếp.",
    "Double elimination settings": "Thiết lập loại kép",
    "Allow a bracket reset": "Cho phép trận quyết định (bracket reset)",
    "If the losers-bracket survivor wins the grand final, both sides have one loss, so a deciding "
    "match is created.":
        "Nếu đội từ nhánh thua thắng chung kết tổng, hai bên đều đã thua một trận nên sẽ có thêm "
        "trận quyết định.",
    "Start a tournament": "Tạo giải đấu",
    "A tournament needs at least one event before it exists — its first category and format are set "
    "up right here, in the same step.":
        "Giải đấu cần ít nhất một nội dung — nội dung và thể thức đầu tiên được thiết lập ngay ở "
        "đây, cùng một bước.",
    "Venue": "Địa điểm",
    "Start date": "Ngày bắt đầu",
    "End date": "Ngày kết thúc",
    "Notes": "Ghi chú",
    "Entry fee, court count, referee list…": "Lệ phí, số sân, danh sách trọng tài…",
    "First event": "Nội dung đầu tiên",
    "Create tournament": "Tạo giải đấu",
    "Give the tournament a name.": "Hãy đặt tên cho giải đấu.",
    "{name} created with its first event ({event}).": "Đã tạo {name} với nội dung đầu tiên ({event}).",
    "All five categories are already in this tournament.": "Giải đấu đã có đủ cả năm nội dung.",
    "Add another event": "Thêm nội dung khác",
    "Add event": "Thêm nội dung",
    "{event} added.": "Đã thêm {event}.",
    "{event} · {format} — {e} entries, {m} matches · {status}":
        "{event} · {format} — {e} đội/VĐV, {m} trận · {status}",
    "Add entries and set up, generate or clear the draw on the **Players & entries** page → Event "
    "entries.":
        "Thêm đội/VĐV và thiết lập, tạo hoặc xóa sơ đồ thi đấu ở trang **Vận động viên & Đăng ký** "
        "→ Đăng ký theo nội dung.",
    "Delete this event": "Xóa nội dung này",
    "Deletes the event, its entries and all its results.":
        "Xóa nội dung, danh sách đăng ký và toàn bộ kết quả.",
    "Yes, delete": "Đồng ý, xóa",
    "Start a new tournament": "Tạo giải đấu mới",
    "Edit tournament details": "Sửa thông tin giải đấu",
    "Save changes": "Lưu thay đổi",
    "Saved.": "Đã lưu.",
    "Events in this tournament": "Các nội dung của giải",
    "No events yet — every tournament is created with one, so this should not normally happen.":
        "Chưa có nội dung — giải nào khi tạo cũng có một nội dung, nên trường hợp này hiếm khi xảy ra.",
    "Danger zone": "Vùng nguy hiểm",
    "Deleting a tournament removes its players, entries and every result.":
        "Xóa giải đấu sẽ xóa toàn bộ VĐV, danh sách đăng ký và kết quả.",
    "Type the tournament name to confirm": "Nhập tên giải đấu để xác nhận",
    "Delete this tournament": "Xóa giải đấu này",
    "The name does not match.": "Tên không khớp.",

    # --- scoring desk ------------------------------------------------------
    "Scoring desk": "Bàn tính điểm",
    "Open matches": "Trận chưa xong",
    "Finished": "Đã kết thúc",
    "Next round": "Vòng tiếp theo",
    "This event has no draw yet. Generate it in Players & entries → Event entries.":
        "Nội dung này chưa có sơ đồ thi đấu. Hãy tạo ở Vận động viên & Đăng ký → Đăng ký theo "
        "nội dung.",
    "Games played": "Số ván đã đấu",
    "Retired?": "Bỏ cuộc?",
    "{name} retired": "{name} bỏ cuộc",
    "Save result": "Lưu kết quả",
    "Result saved.": "Đã lưu kết quả.",
    "Reload this match": "Tải lại trận này",
    "{who} is scoring this match right now. Check with them before you save.":
        "{who} đang tính điểm trận này. Hãy trao đổi với họ trước khi lưu.",
    "Every match here is finished.": "Tất cả trận ở đây đã kết thúc.",
    "← All matches": "← Tất cả trận",
    "Score →": "Tính điểm →",
    "On court ({n})": "Đang thi đấu ({n})",
    "Ready to call ({n})": "Sẵn sàng gọi vào sân ({n})",
    "Waiting on earlier results ({n})": "Chờ kết quả trận trước ({n})",
    "No completed matches yet.": "Chưa có trận nào kết thúc.",
    "{n} completed. Use 'Correct this result' if the desk typed it wrong.":
        "{n} trận đã xong. Dùng 'Sửa kết quả này' nếu nhập nhầm.",
    "Correct this result": "Sửa kết quả này",
    "Walkovers are corrected by editing the entry list.":
        "Trận xử thắng được sửa bằng cách chỉnh danh sách đăng ký.",
    "Reopen": "Mở lại",
    "Reopened. It is back in Open matches — score it again there.":
        "Đã mở lại. Trận đã về mục Trận chưa xong — hãy tính điểm lại ở đó.",
    "Reopening pulls the winner back out of the next round, so it only works while that next match "
    "has not started.":
        "Mở lại sẽ rút đội thắng khỏi vòng sau, nên chỉ làm được khi trận tiếp theo chưa bắt đầu.",
    "Round {a} of {b} scheduled.": "Đã xếp vòng {a}/{b}.",
    "Pair round {n}": "Ghép cặp vòng {n}",
    "Round {n} paired, but a rematch was unavoidable. Check the Fixtures page.":
        "Đã ghép cặp vòng {n}, nhưng không tránh được việc gặp lại. Hãy kiểm tra trang Lịch thi đấu.",
    "Round {n} paired.": "Đã ghép cặp vòng {n}.",
    "Playoff bracket is live.": "Nhánh loại trực tiếp đang diễn ra.",
    "Generate playoff bracket": "Tạo nhánh loại trực tiếp",
    "Playoff bracket created.": "Đã tạo nhánh loại trực tiếp.",
    "Finish every pool match, then the playoff bracket unlocks here.":
        "Hoàn thành mọi trận vòng bảng, nhánh loại trực tiếp sẽ mở ở đây.",
    "This format schedules itself — results feed the next round automatically.":
        "Thể thức này tự xếp lịch — kết quả tự động chuyển sang vòng sau.",

    # --- referee board -----------------------------------------------------
    "Tablet full-screen (hide the menu)": "Toàn màn hình máy tính bảng (ẩn menu)",
    "Game {a} of {b}": "Ván {a}/{b}",
    "Games {a}–{b}": "Tỉ số ván {a}–{b}",
    "{team} won the rally": "{team} thắng pha bóng",
    "✅ Confirm game to {team}  ({a}–{b})": "✅ Xác nhận {team} thắng ván  ({a}–{b})",
    "↶ Undo": "↶ Hoàn tác",
    "Undone.": "Đã hoàn tác.",
    "⏱ Timeout ◀ ({a}/{b})": "⏱ Hội ý ◀ ({a}/{b})",
    "⏱ Timeout ▶ ({a}/{b})": "⏱ Hội ý ▶ ({a}/{b})",
    "Timeout — {team} (1 minute).": "Hội ý — {team} (1 phút).",
    "⇄ Switch ends": "⇄ Đổi sân",
    "Timeouts {a}/{b}": "Hội ý {a}/{b}",
    "KITCHEN": "VÙNG CẤM",
    "Right · even": "Phải · chẵn",
    "Left · odd": "Trái · lẻ",
    "<b>{server}</b> serves from the <b>{court}</b> court": "<b>{server}</b> giao bóng từ ô <b>{court}</b>",
    "Game — {team}": "Hết ván — {team}",
    "Game point — {team}": "Điểm ván — {team}",
    "Match point — {team}": "Điểm trận — {team}",
    "Game to {team} — confirm it below (or Undo if that rally was wrong).":
        "{team} thắng ván — xác nhận bên dưới (hoặc Hoàn tác nếu ghi nhầm pha bóng).",
    "🔄 Switch ends now! Both sides change ends.": "🔄 Đổi sân ngay! Hai bên đổi phần sân.",
    "Side out — {team} to serve: {server}.": "Đổi giao bóng — {team} giao: {server}.",
    "Second server: {server}.": "Người giao thứ hai: {server}.",
    "🏆 Match complete.": "🏆 Trận đấu kết thúc.",
    "Game locked in. New game: sides change ends — check the serve below.":
        "Đã chốt ván. Ván mới: hai bên đổi sân — kiểm tra quyền giao bóng bên dưới.",
    "🎾 Serve setup for this game": "🎾 Thiết lập giao bóng cho ván này",
    "Serves first": "Giao bóng trước",
    "Who starts in the **right (even) court**? They serve first for their side.":
        "Ai bắt đầu ở **ô phải (chẵn)**? Người đó giao bóng trước cho bên mình.",
    "Save serve setup": "Lưu thiết lập giao bóng",
    "Serve setup saved.": "Đã lưu thiết lập giao bóng.",
    "✏️ Edit player names": "✏️ Sửa tên VĐV",
    "✏️ Check / edit player names before the match": "✏️ Kiểm tra / sửa tên VĐV trước trận",
    "Corrects the name everywhere it appears — other events, draws, standings, the live board. Seeds, "
    "draw positions and results stay exactly as they are.":
        "Sửa tên ở mọi nơi — các nội dung khác, sơ đồ thi đấu, bảng xếp hạng, bảng trực tiếp. "
        "Hạt giống, vị trí trong sơ đồ và kết quả giữ nguyên.",
    "Side {s} player {n}": "Bên {s} — VĐV {n}",
    "Save names": "Lưu tên",
    "{n} name(s) updated everywhere.": "Đã cập nhật {n} tên ở mọi nơi.",
    "No names changed.": "Không có tên nào thay đổi.",
    "🔧 Correct the score by hand": "🔧 Sửa điểm thủ công",
    "For fixing a mistake the rules can't undo. Rally buttons and Undo are the normal way to score.":
        "Dùng để sửa lỗi mà Hoàn tác không xử lý được. Bình thường hãy dùng nút pha bóng và "
        "Hoàn tác.",
    "Court": "Sân",
    "e.g. Court 3": "VD: Sân 3",
    "Save court": "Lưu sân",
    "Undo the last confirmed game": "Hoàn tác ván vừa xác nhận",
    "Last game reopened.": "Đã mở lại ván vừa rồi.",
    "Retire a side, or type the whole score in by hand": "Xử bỏ cuộc, hoặc nhập toàn bộ tỉ số thủ công",
    "▶ Start match": "▶ Bắt đầu trận",

    # --- quick match -------------------------------------------------------
    "Quick match": "Trận đấu nhanh",
    "Not part of any tournament": "Không thuộc giải đấu nào",
    "Start a quick match": "Bắt đầu trận đấu nhanh",
    "Two names (four for doubles) and a scoring format — nothing else to set up. This never touches "
    "any tournament's draws, entries, or standings.":
        "Hai tên (bốn tên nếu đánh đôi) và cách tính điểm — không cần thiết lập gì thêm. Không "
        "ảnh hưởng đến sơ đồ, danh sách hay bảng xếp hạng của giải nào.",
    "Side A partner (doubles only)": "Đồng đội bên A (chỉ đánh đôi)",
    "Side B partner (doubles only)": "Đồng đội bên B (chỉ đánh đôi)",
    "leave empty for singles": "để trống nếu đánh đơn",
    "Start match": "Bắt đầu trận",
    "Both names are required.": "Cần nhập tên cả hai bên.",
    "Nothing in progress right now — see finished matches below.":
        "Hiện không có trận nào đang diễn ra — xem các trận đã xong bên dưới.",
    "No quick matches yet — start one above.": "Chưa có trận đấu nhanh — hãy bắt đầu ở trên.",
    "Recently finished": "Vừa kết thúc",

    # --- courts ------------------------------------------------------------
    "Courts": "Sân đấu",
    "Court name": "Tên sân",
    "Court 1": "Sân 1",
    "Add court": "Thêm sân",
    "Or add numbered courts": "Hoặc thêm sân theo số",
    "Prefix": "Tiền tố",
    "Add them": "Thêm",
    "No courts yet. Add them above so matches can be called on.":
        "Chưa có sân. Hãy thêm sân ở trên để gọi trận.",
    "Add courts on the Courts tab first.": "Hãy thêm sân ở thẻ Sân đấu trước.",
    "Courts right now": "Tình trạng sân",
    "Next to be called": "Trận sắp được gọi",
    "{n} court(s) free. Players already on court in another category are skipped automatically.":
        "{n} sân trống. VĐV đang thi đấu ở nội dung khác sẽ tự động được bỏ qua.",
    "Call these {n} match(es) on": "Gọi {n} trận này vào sân",
    "{n} match(es) started.": "Đã bắt đầu {n} trận.",
    "Nothing can be called right now.": "Hiện chưa có trận nào gọi được.",
    "Held back ({n})": "Tạm hoãn ({n})",
    "{p} is playing {event}{where}": "{p} đang thi đấu {event}{where}",
    "No matches are ready to call.": "Chưa có trận nào sẵn sàng để gọi.",
    "Match": "Trận",
    "Player clash: {x}": "Trùng VĐV: {x}",
    "{court} already has a live match on it.": "{court} đang có trận diễn ra.",
    "No clash. Safe to call on.": "Không trùng. Có thể gọi vào sân.",
    "Call it on anyway": "Vẫn gọi vào sân",
    "Use this when a player has agreed to play back to back, or you are moving a match mid-flight.":
        "Dùng khi VĐV đồng ý đấu liền hai trận, hoặc khi chuyển sân giữa trận.",
    "Call this match on": "Gọi trận này vào sân",
    "Tick 'Call it on anyway' to override the clash.": "Tích 'Vẫn gọi vào sân' để bỏ qua trùng lịch.",
    "Called on.": "Đã gọi vào sân.",
    "Nobody has matches outstanding.": "Không ai còn trận chờ.",
    "Players with matches still to play, busiest first. Use this to spot someone who is about to be "
    "pulled three ways at once.":
        "VĐV còn trận chưa đấu, nhiều trận nhất xếp trước. Dùng để phát hiện người sắp bị xếp "
        "đấu nhiều nơi cùng lúc.",
    "Entered in": "Tham gia",
    "Matches left": "Trận còn lại",
    "Call next": "Gọi trận tiếp",
    "Assign manually": "Xếp thủ công",
    "Player load": "Lịch VĐV",

    # --- fixtures ----------------------------------------------------------
    "Fixtures": "Lịch thi đấu",
    "Fixture": "Cặp đấu",
    "Nothing left to change — every match is finished.": "Không còn gì để sửa — mọi trận đã xong.",
    "This match is on court. Changing it now will confuse the referee.":
        "Trận này đang diễn ra. Thay đổi lúc này sẽ gây nhầm lẫn cho trọng tài.",
    "Entry A": "Đội A",
    "Entry B": "Đội B",
    "{a} and {b} already meet in: {where}": "{a} và {b} đã gặp nhau ở: {where}",
    "{a} vs {b} is a first meeting.": "{a} gặp {b} lần đầu.",
    "Allow a rematch anyway": "Vẫn cho phép gặp lại",
    "Use this when a Swiss round genuinely has no rematch-free pairing.":
        "Dùng khi vòng Thụy Sĩ thật sự không thể ghép cặp mà không gặp lại.",
    "Save this fixture": "Lưu cặp đấu này",
    "Fixture updated.": "Đã cập nhật cặp đấu.",
    "You need at least two unplayed fixtures to swap between.": "Cần ít nhất hai cặp đấu chưa đá để hoán đổi.",
    "Exchange one side between two fixtures. Both resulting pairings are checked for repeats before "
    "anything is written.":
        "Đổi một bên giữa hai cặp đấu. Cả hai cặp mới được kiểm tra trùng trước khi lưu.",
    "First fixture": "Cặp đấu thứ nhất",
    "Second fixture": "Cặp đấu thứ hai",
    "Swapping {a} ↔ {b}": "Hoán đổi {a} ↔ {b}",
    "Swap them": "Hoán đổi",
    "Swapped.": "Đã hoán đổi.",
    "No open fixtures.": "Không có cặp đấu nào chưa đá.",
    "Assign courts ahead of time so the Live board can show where to go.":
        "Xếp sân trước để bảng trực tiếp hiển thị nơi thi đấu.",
    "Save court assignments": "Lưu xếp sân",
    "{n} court(s) updated.": "Đã cập nhật {n} sân.",
    "No pair is scheduled to meet more than once in this event.":
        "Không có cặp nào gặp nhau quá một lần trong nội dung này.",
    "{n} pair(s) meet more than once. That is expected in a double-elimination bracket, and worth a "
    "second look anywhere else.":
        "{n} cặp gặp nhau nhiều hơn một lần. Điều này bình thường ở thể thức loại kép, nhưng nên "
        "kiểm tra lại ở các thể thức khác.",
    "{n} fixture(s) still waiting on an earlier result.": "{n} cặp đấu đang chờ kết quả trận trước.",
    "This event has no draw yet.": "Nội dung này chưa có sơ đồ thi đấu.",
    "Reassign a fixture": "Sắp xếp lại cặp đấu",
    "Swap two sides": "Hoán đổi hai bên",
    "Repeat check": "Kiểm tra trùng lặp",

    # --- engine errors -----------------------------------------------------
    "A game cannot end level.": "Ván đấu không thể kết thúc với tỉ số hòa.",
    "A match is on this court right now.": "Sân này đang có trận diễn ra.",
    "A player cannot partner themselves.": "VĐV không thể đánh cặp với chính mình.",
    "An entry cannot play itself.": "Một đội không thể tự đấu với chính mình.",
    "Add at least one match.": "Hãy thêm ít nhất một trận.",
    "Another player in this tournament is already called {name}.":
        "Đã có VĐV khác trong giải tên là {name}.",
    "Best of {n}: someone needs {need} game(s) to win.":
        "Đấu {n} ván: cần thắng {need} ván để thắng trận.",
    "Both sides must be decided before a score can be saved.":
        "Phải có đủ hai bên mới lưu được tỉ số.",
    "Both sides must be decided before the match can start.":
        "Phải có đủ hai bên mới bắt đầu được trận.",
    "Capped game still needs a one-point margin.": "Ván có điểm tối đa vẫn cần cách biệt một điểm.",
    "Custom brackets are built round by round in the Draw section, not generated here.":
        "Nhánh tự xếp được dựng từng vòng ở phần Sơ đồ thi đấu, không tạo tự động ở đây.",
    "Doubles entries need two players.": "Đăng ký đánh đôi cần hai VĐV.",
    "Drag every entry into a pool (Draw section of Event entries) before generating a manual draw.":
        "Hãy kéo mọi đội vào bảng (phần Sơ đồ thi đấu trong Đăng ký theo nội dung) trước khi tạo "
        "sơ đồ thủ công.",
    "Enter at least one game.": "Hãy nhập ít nhất một ván.",
    "Entry not found.": "Không tìm thấy đội.",
    "Event not found.": "Không tìm thấy nội dung.",
    "Every entry needs a recorded position before generating a manual draw — record the order in "
    "the Draw section first.":
        "Mọi đội cần có vị trí trước khi tạo sơ đồ thủ công — hãy ghi nhận thứ tự ở phần Sơ đồ "
        "thi đấu trước.",
    "Finish every pool match before generating the playoffs.":
        "Hãy hoàn thành mọi trận vòng bảng trước khi tạo vòng loại trực tiếp.",
    "Finished matches cannot be re-drawn. Reopen the match first.":
        "Không thể xếp lại trận đã xong. Hãy mở lại trận trước.",
    "For doubles, give a partner on both sides (or neither for singles).":
        "Đánh đôi cần nhập đồng đội cho cả hai bên (đánh đơn thì để trống cả hai).",
    "Game {i} was not needed — the match was already decided.":
        "Ván {i} là thừa — trận đấu đã phân thắng bại.",
    "Game {i}: {err}": "Ván {i}: {err}",
    "Give the court a name.": "Hãy đặt tên cho sân.",
    "Match not found.": "Không tìm thấy trận.",
    "Mixed Doubles normally pairs one man and one woman.": "Đôi nam nữ thường gồm một nam và một nữ.",
    "Names cannot be empty.": "Tên không được để trống.",
    "Need at least {n} entries to build this draw.": "Cần ít nhất {n} đội để tạo sơ đồ này.",
    "No confirmed games to undo yet.": "Chưa có ván nào được xác nhận để hoàn tác.",
    "No rematch-free pairing exists for this round.":
        "Vòng này không có cách ghép cặp nào tránh được việc gặp lại.",
    "No timeouts left (each side gets {n} per game).": "Hết lượt hội ý (mỗi bên có {n} lượt mỗi ván).",
    "Not enough qualifiers for a playoff bracket.": "Không đủ đội để tạo nhánh loại trực tiếp.",
    "Nothing to undo in this game yet.": "Chưa có gì để hoàn tác trong ván này.",
    "One of these matches is live or finished.": "Một trong hai trận đang diễn ra hoặc đã xong.",
    "Pair up at least one match before creating round 1.": "Hãy ghép ít nhất một trận trước khi tạo vòng 1.",
    "Past {n} the game ends the moment someone leads by {w}.":
        "Sau {n} điểm, ván kết thúc ngay khi một bên dẫn {w} điểm.",
    "Pick a different player to bring in.": "Hãy chọn một VĐV khác để vào thay.",
    "Player name cannot be empty.": "Tên VĐV không được để trống.",
    "Player not found.": "Không tìm thấy VĐV.",
    "Playoffs have already been generated.": "Vòng loại trực tiếp đã được tạo.",
    "Round {r} still has {n} match(es) to finish.": "Vòng {r} còn {n} trận chưa xong.",
    "All {n} scheduled Swiss rounds are complete.": "Đã hoàn thành cả {n} vòng Thụy Sĩ.",
    "Score is capped at {n}.": "Điểm tối đa là {n}.",
    "Scores cannot be negative.": "Điểm không được âm.",
    "Serve order can only be changed before the first rally of a game. Undo back to 0-0 first.":
        "Chỉ đổi được thứ tự giao bóng trước pha bóng đầu tiên của ván. Hãy hoàn tác về 0-0 trước.",
    "Start the match before adjusting points.": "Hãy bắt đầu trận trước khi chỉnh điểm.",
    "Start the match first.": "Hãy bắt đầu trận trước.",
    "That player isn't part of this entry.": "VĐV này không thuộc đội này.",
    "That swap creates a repeat matchup: {x}": "Hoán đổi này tạo ra cặp gặp lại: {x}",
    "This entry already has a live or completed match. Withdraw them instead.":
        "Đội này đã có trận đang đấu hoặc đã xong. Hãy cho rút lui thay vì xóa.",
    "This event already has a draw. Clear it first.": "Nội dung này đã có sơ đồ. Hãy xóa trước.",
    "This event already has matches. Clear the draw first.": "Nội dung này đã có trận. Hãy xóa sơ đồ trước.",
    "This game is already over — confirm it or undo.": "Ván này đã kết thúc — hãy xác nhận hoặc hoàn tác.",
    "This match is already finished.": "Trận này đã kết thúc.",
    "This match isn't live.": "Trận này chưa diễn ra.",
    "This player is on an entry. Remove the entry first.": "VĐV này đang có trong một đội. Hãy xóa đội trước.",
    "Unknown category {x}": "Nội dung không hợp lệ: {x}",
    "Unknown scoring system {x}": "Luật tính điểm không hợp lệ: {x}",
    "Unsupported format {x}": "Thể thức không được hỗ trợ: {x}",
    "Winner must lead by {w}.": "Bên thắng phải dẫn {w} điểm.",
    "Winning score must reach {n}.": "Điểm thắng phải đạt {n}.",
    "side must be 'a' or 'b'.": "bên phải là 'a' hoặc 'b'.",
    "Side {s} positions don't match their score — check who is on the right.":
        "Vị trí bên {s} không khớp với điểm — hãy kiểm tra ai đứng ô phải.",
    "{a} and {b} already meet in: {where}. Tick 'allow rematch' if that is intended.":
        "{a} và {b} đã gặp nhau ở: {where}. Tích 'cho phép gặp lại' nếu đó là chủ ý.",
    "{event} already exists in this tournament.": "{event} đã có trong giải đấu này.",
    "{event} normally requires {g} players.": "{event} thường yêu cầu VĐV {g}.",
    "{m} has already started. Reopen that one first.": "{m} đã bắt đầu. Hãy mở lại trận đó trước.",
    "{name} is already entered elsewhere in {event}.": "{name} đã có trong một đội khác ở {event}.",
    "{name} is already entered in {event}.": "{name} đã đăng ký {event}.",
    "{name} is already this entry's other half.": "{name} đã là đồng đội trong đội này.",
    "{name} isn't eligible for this slot in {event} (needs a man).":
        "{name} không phù hợp vị trí này ở {event} (cần VĐV nam).",
    "{name} isn't eligible for this slot in {event} (needs a woman).":
        "{name} không phù hợp vị trí này ở {event} (cần VĐV nữ).",
    "{who} saved this match a moment ago. Reload to see the current score before saving again.":
        "{who} vừa lưu trận này. Hãy tải lại để xem tỉ số hiện tại trước khi lưu tiếp.",
}
