; -- prologd.iss --
; Установщик «Пролог-Д» для одного пользователя (task_116).
;
; Ставится то же, что лежит в переносимом пакете: окно, оба движка, руководства и
; примеры, — плюс, если попросят, связь файлов .pld с окном.
;
; Собирается из tools\build_installer.ps1, который передаёт версию:
;   ISCC.exe --define=AppVersion=2.6.1 installer\prologd.iss
; Версия ниже — только значение по умолчанию для ручного запуска.
;
; Файл сохранён в UTF-8 **с BOM**: без BOM Inno Setup читает .iss как ANSI и
; превращает кириллицу в мусор.

#ifndef AppVersion
  #define AppVersion "2.6.1"
#endif

; Имя продукта в установщике — без «2.0»: это имя оболочки, и рядом с номером
; версии оно читалось как два номера подряд («Пролог-Д 2.0 2.6.1», task_116).
; В окне, руководствах и «О программе» название «Пролог-Д 2.0» остаётся.
#define AppName "Пролог-Д"
; Идентификатор связи. Он же имя класса файлов в реестре и, главное, — признак
; «это наша связь»: по нему решается, забирать ли .pld у чужой программы и
; удалять ли значение при деинсталляции.
#define ProgId "PrologD.Program"

[Setup]
; Постоянный AppId — то, что заставляет новую версию *заменять* прежнюю, а не
; вставать рядом. Менять нельзя никогда: смена AppId превращает обновление в
; вторую установку.
AppId={{7B1F3C42-5D2E-4A6B-9C1D-2E8F4A7B9C31}
AppName={#AppName}
AppVerName={#AppName} {#AppVersion}
AppVersion={#AppVersion}
AppPublisher=PrologD
VersionInfoVersion={#AppVersion}
; Свойства файла установщика: без них Inno подставляет сюда AppVerName, и в
; свойствах получается «Пролог-Д 2.6.1 Setup».
VersionInfoDescription={#AppName} — установщик
VersionInfoProductName={#AppName}

; Один пользователь, без UAC: настройки окна лежат в %LOCALAPPDATA%\PrologD\gui,
; и делить между учётными записями нечего.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\PrologD
; Папка фиксирована намеренно: paths.settings_path() решает «установленная или
; переносимая» по папке, из которой запущено окно, и установка в другое место
; повела бы себя как переносимая копия — со своим gui.ini рядом с exe (task_116).
DisableDirPage=yes
UsePreviousAppDir=no
DisableProgramGroupPage=yes
DefaultGroupName={#AppName}

; Windows 10 1903 и новее, 64 бита — тот же порог, что в README репозитория и в
; руководстве окна.
MinVersion=10.0.18362
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

OutputDir=..\dist
OutputBaseFilename=prologd-{#AppVersion}-setup
SetupIconFile=..\src\gui\assets\prologd2.ico
UninstallDisplayIcon={app}\prologd-gui.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern dynamic
; Без этого оболочка не узнает, что .pld сменил хозяина.
ChangesAssociations=yes

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
; Каждая своя строка есть на обоих языках: иначе английская установка показывает
; русский текст — именно это владелец увидел в строке «Связь с файлами» и в
; вопросе при удалении (task_116). Встроенные {cm:...} переводятся самими .isl.
ru.AssociateTask=Открывать файлы .pld двойным щелчком в «{#AppName}»
ru.AssociateGroup=Связь с файлами:
ru.GuideIcon=Руководство «{#AppName}»
ru.DeleteSettings=Удалить настройки окна — сессию, список недавних файлов и шрифты?
ru.FileTypeName=Программа Пролог-Д
ru.ConsoleVerb=Запустить в консоли
en.AssociateTask=Open .pld files with a double-click
en.AssociateGroup=File association:
en.GuideIcon=Manual
en.DeleteSettings=Delete the window settings — the session, the recent files and the fonts?
en.FileTypeName=PrologD program
en.ConsoleVerb=Run in console

[Tasks]
Name: "associate"; Description: "{cm:AssociateTask}"; GroupDescription: "{cm:AssociateGroup}"; Flags: checkedonce
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Весь переносимый пакет, кроме исходников руководств: пакет их уже не несёт
; (task_116), а старый пакет, собранный до этого решения, не должен их протащить.
; Своего read-me у пакета больше нет — памятка жила в нём, а всё, что она
; объясняла, есть в doc\gui.pdf.
Source: "..\dist\prologd-{#AppVersion}-win64\*"; DestDir: "{app}"; Excludes: "*.typ"; Flags: ignoreversion recursesubdirs createallsubdirs
; Значок .pld отдельным файлом: в пакете его нет, он нужен только реестру.
Source: "..\src\gui\assets\pld.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\prologd-gui.exe"
Name: "{autoprograms}\{cm:GuideIcon}"; Filename: "{app}\doc\help.pdf"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\prologd-gui.exe"; Tasks: desktopicon

[Registry]
; .pld → наш ProgId. Флага uninsdeletevalue здесь нет намеренно: удаляет значение
; [Code] и только если расширение всё ещё наше (пользователь мог отдать его
; другой программе после установки).
Root: HKA; Subkey: "Software\Classes\.pld"; ValueType: string; ValueName: ""; ValueData: "{#ProgId}"; Tasks: associate
; Описание класса и глагол меню видны в проводнике, а не в мастере.  Текст берётся
; из [CustomMessages]: параметр Languages у [Registry] проверку не прошёл - обе
; записи всё равно попадали в файл, и английская перекрывала русскую.
Root: HKA; Subkey: "Software\Classes\{#ProgId}"; ValueType: string; ValueName: ""; ValueData: "{cm:FileTypeName}"; Flags: uninsdeletekey; Tasks: associate
Root: HKA; Subkey: "Software\Classes\{#ProgId}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\pld.ico"; Tasks: associate
Root: HKA; Subkey: "Software\Classes\{#ProgId}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\prologd-gui.exe"" ""%1"""; Tasks: associate
; Второй глагол контекстного меню: тот же файл, но в консольном интерпретаторе.
; Только если этот движок в пакете есть: сборка «только d» его не несёт.
Root: HKA; Subkey: "Software\Classes\{#ProgId}\shell\console"; ValueType: string; ValueName: ""; ValueData: "{cm:ConsoleVerb}"; Tasks: associate; Check: FileExists(ExpandConstant('{app}\prologu.exe'))
Root: HKA; Subkey: "Software\Classes\{#ProgId}\shell\console\command"; ValueType: string; ValueName: ""; ValueData: """{app}\prologu.exe"" -s ""%1"""; Tasks: associate; Check: FileExists(ExpandConstant('{app}\prologu.exe'))

; App Paths: `prologu` и `prologd` находятся из любого каталога и из Win+R, хотя
; PATH не правится. Каждая запись — только если файл действительно установлен:
; пакет сборки «только d» не несёт prologu.exe.
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\prologu.exe"; ValueType: string; ValueName: ""; ValueData: "{app}\prologu.exe"; Flags: uninsdeletekey; Check: FileExists(ExpandConstant('{app}\prologu.exe'))
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\prologu.exe"; ValueType: string; ValueName: "Path"; ValueData: "{app}"; Check: FileExists(ExpandConstant('{app}\prologu.exe'))
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\prologd.exe"; ValueType: string; ValueName: ""; ValueData: "{app}\prologd.exe"; Flags: uninsdeletekey; Check: FileExists(ExpandConstant('{app}\prologd.exe'))
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\prologd.exe"; ValueType: string; ValueName: "Path"; ValueData: "{app}"; Check: FileExists(ExpandConstant('{app}\prologd.exe'))

[Run]
Filename: "{app}\prologd-gui.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Окно установленной копии пишет настройки в AppData, но старый gui.ini рядом
; с exe (если кто-то его туда положил) тоже наш.
Type: files; Name: "{app}\gui.ini"

[Code]
var
  { .pld уже принадлежит другой программе — тогда галочку связи не ставим. }
  ForeignHandler: Boolean;

function InitializeSetup(): Boolean;
var
  Current: String;
begin
  ForeignHandler :=
    RegQueryStringValue(HKCU, 'Software\Classes\.pld', '', Current)
    and (CompareText(Current, '{#ProgId}') <> 0);
  Result := True;
end;

procedure InitializeWizard();
begin
  { Связь предлагается по умолчанию, но не тогда, когда расширение уже чужое:
    галочка снимается, а поставить её руками по-прежнему можно. }
  if ForeignHandler then
    WizardSelectTasks('');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Current: String;
  Settings: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    { Настройки: спрашиваем и по умолчанию соглашаемся — «при деинсталляции
      обязательно удалять все артефакты» (task_116). Молча ничего не трогаем.
      Вопрос берётся из [CustomMessages], чтобы в английской установке он был
      английским: язык запоминается в данных удаления. }
    Settings := ExpandConstant('{localappdata}\PrologD');
    if (not UninstallSilent()) and DirExists(Settings) then
      if MsgBox(ExpandConstant('{cm:DeleteSettings}') + #13#10#13#10 + Settings,
                mbConfirmation, MB_YESNO or MB_DEFBUTTON1) = IDYES then
        DelTree(Settings, True, True, True);
  end
  else if CurUninstallStep = usPostUninstall then
  begin
    { Расширение убираем, только если оно всё ещё указывает на нас: если
      пользователь отдал .pld другой программе, это его выбор, и он остаётся.
      Удалив значение, убираем и саму ветку, если она опустела, — иначе в HKCU
      остаётся пустой ключ .pld, который виден любому, кто смотрит ассоциации. }
    if RegQueryStringValue(HKCU, 'Software\Classes\.pld', '', Current)
       and (CompareText(Current, '{#ProgId}') = 0) then
    begin
      RegDeleteValue(HKCU, 'Software\Classes\.pld', '');
      RegDeleteKeyIfEmpty(HKCU, 'Software\Classes\.pld');
    end;
  end;
end;
