# ArtCraft for iPad (VectorCraft · PhotoCraft · FilmCraft · LightCraft · CadCraft · SoundCraft)

ArtCraft의 오픈소스 앱(MIT / Apache-2.0)을 iPad 홈 화면 앱처럼 쓰기 위한 개인용 배포 저장소입니다.
하루에 한 번 원본 웹 빌드를 받아 오프라인 캐시 파일을 붙여 GitHub Pages에 올립니다.
받은 zip은 이 저장소의 Releases(`backup-vectorcraft`, `backup-photocraft`, `backup-filmcraft`, `backup-lightcraft`, `backup-cadcraft`, `backup-soundcraft`)에 자동으로 백업되고,
원본이 사라지거나 검증(SHA256)에 실패하면 백업본으로 사이트를 계속 만듭니다.

- 앱 목록: `apps.json` (앱을 더 넣으려면 항목만 추가)
- 개인용입니다. ArtCraft 이름·로고는 상표이므로 앱 설정·문구를 고쳐서 다시 배포하지 마세요.

## 올리는 순서
1. GitHub에서 **Public** 저장소 `artcraft-ipad` 생성
2. 이 폴더의 `apps.json`, `README.md`, `icons`, `scripts`, `templates` 를 업로드
3. **`.github/workflows/deploy.yml`** 은 드래그로 올라가지 않을 수 있습니다.
   Add file → Create new file → 파일명에 `.github/workflows/deploy.yml` 입력 → 내용 붙여넣기 → Commit
4. Settings → Pages → Source: **GitHub Actions**
5. Actions → *Deploy ArtCraft apps for iPad* → Run workflow (Pages를 켜기 전에 실패했다면 다시 실행)
6. 완료 후 `https://toyazzang.github.io/artcraft-ipad/` 접속

## iPad
1. Safari로 위 주소를 열고, 앱 카드를 눌러 연 뒤 공유 → 홈 화면에 추가
2. 인터넷이 되는 곳에서 홈 화면 아이콘으로 1~2분 켜 둠 (VectorCraft 약 68MB, FilmCraft 약 41MB, LightCraft 약 26MB, CadCraft 약 23MB, SoundCraft 약 16MB)
3. 비행기 모드에서 아이콘을 눌러 열리는지 확인

새 버전은 하루 안에 사이트에 반영되고, iPad에서는 온라인으로 앱을 연 다음 실행부터 적용됩니다.
저장소에 60일간 활동이 없으면 예약 실행이 멈추니, 가끔 Run workflow를 눌러 주세요.

## 메모
- PhotoCraft는 원본이 손가락·Pencil 터치로 File/Edit 메뉴바를 열지 못해서, 상단 바의 터치를 마우스 입력으로 넘기는 코드를 `apps.json`의 `menubar_touch_px`로 넣었습니다. 원본이 고쳐지면 그 줄을 지우세요.
- 앱 추가: `apps.json`에 항목을 넣고 `icons/<id>/icon-{180,192,512}.png`를 만들면 됩니다.
- 웹 빌드에는 한글 폰트가 없어 한국어 환경에서는 영어 UI로 표시합니다.
- VectorCraft 주소는 `https://toyazzang.github.io/artcraft-ipad/vectorcraft/` 입니다. 예전 `vectorcraft-ipad` 저장소는 그대로 두면 계속 동작하니, 새 주소에서 홈 화면에 추가해 잘 열리는 것을 확인한 뒤 정리하세요.
