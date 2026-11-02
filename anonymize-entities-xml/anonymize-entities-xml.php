#!/usr/bin/env php
<?php

$dateOffset = new DateInterval( sprintf( 'P%dD', rand( 1000, 5000 ) ) );

const FIRST_NAMES = [ 'Max' ]; # TODO read in a longer list
const LAST_NAMES = [ 'Mustermann' ]; # TODO read in a longer list
/* decided by chance: shuf /usr/share/dict/ngerman | head -n 256 */
const TITLE_COMPONENTS = [ 'zückendes', 'Klimmzuges', 'Begrenzungsmauer', 'handlungsunfähigen', 'beistellendem', 'Unterkunft', 'zweiundneunzigstes',
'rückhaltlosem', 'Grundüberlegungen', 'Fortentwickelung', 'saugfähigsten', 'unerschlossenst', 'dünstendes', 'verschütteter', 'merkbaren', 'spektakulär',
'resorbiertes', 'Nachttischleuchten', 'granulieren', 'manövrierende', 'geschleuster', 'beliegen', 'Himmelsereignisses', 'tröstenden', 'Einsteins',
'Tanten', 'Panschern', 'weltabgewandteren', 'bezugsfrei', 'Atomstopp', 'Insulins', 'Wirrsale', 'unbenutztem', 'beimessen', 'schwelgenden',
'ereignisloser', 'aufgeforderten', 'aufgehetztem', 'exquisiten', 'ungefährlichster', 'mittelständischem', 'entseelten', 'Schlaflosigkeit',
'Koks', 'ungeküsster', 'Sofortmaßnahme', 'störendes', 'draufgehender', 'festnagelten', 'hineinsehen', 'Lahr', 'unmoderneren', 'umbindest',
'Jugendliteratur', 'gutwillig', 'Coprozessor', 'Kupplungssteuerungsgerätes', 'unnatürlichere', 'günstigstem', 'anzubauendes', 'Gesamtimporte',
'weiterhelfendes', 'vorgesehenen', 'steganografische', 'Fords', 'abgesondertster', 'kränkendem', 'paradox', 'Zielmaschinensprachen',
'durchhaltender', 'vollpissendem', 'Proviants', 'stattzufindendes', 'Königsstuhl', 'Standfotos', 'knobeln', 'inakzeptablem', 'unmarkiertem',
'Ölfarben', 'fauchendem', 'attribuierbarem', 'abstillten', 'verleumdete', 'Hauptdarstellern', 'Assessor', 'Schneewehe', 'Heimreisen', 'acta',
'Klassenkämpfern', 'Familienzuschüsse', 'auswanderndem', 'verbotenen', 'brüskiertest', 'skizzenhafter', 'anzulassen', 'stiefele', 'Infiltrierung',
'Kanzlernachfolge', 'wiedergegebenen', 'piezoelektrischer', 'gepackt', 'eindringender', 'ungelehrteste', 'paralysiert', 'abzuschneidend',
'Sattelplatz', 'unerschöpflichstes', 'Freisetzung', 'sorgsame', 'abgesegnetes', 'bluffender', 'Sortimentes', 'Netzwerke', 'nominelles', 'geprägtem',
'aufstampfendes', 'Vorenthaltung', 'Büchner', 'einwählten', 'kabbelst', 'verkrustendes', 'informativster', 'eigenständiger', 'Ortsteile',
'Funktionsdiagramme', 'DKP', 'herabgewirtschaftet', 'divergierst', 'einlade', 'epischer', 'gefallsüchtig', 'Platinenanschraubwinkel', 'mautpflichtiges',
'Widerrede', 'bezauberter', 'triefst', 'Güterart', 'Hühnchens', 'ausschertet', 'Meinungsbildner', 'hinschlage', 'artistischem', 'untoter', 'verblödenden',
'Setzreises', 'Brauereigewerbe', 'Anlage', 'herumschleppende', 'erhängtest', 'beiliegt', 'kribbele', 'Dollarlücke', 'gleitende', 'Trockendock',
'hervorragenderes', 'durchdrückten', 'erfrischtes', 'herunterschiebendem', 'abzuringendem', 'Gehäusepreises', 'erzwingendes', 'ökologischst', 'umspielt',
'entgoltenen', 'Haushaltsjahr', 'aufpeppendem', 'Kantor', 'herunterbringenden', 'überwarf', 'energischeren', 'zahlungskräftigste', 'Saga', 'Gehäusevarianten',
'abzuhandelndes', 'Gesellschaftshauses', 'tremolierenden', 'kalorienreich', 'kennenlernenden', 'Instanziierung', 'Vertragens', 'Sprechübungen',
'rechtlichen', 'kuschelnd', 'Hierarchisierens', 'Netzteilsicherung', 'verzärtele', 'unterbesetztes', 'filmtet', 'Ackerbauern', 'hereinschaue',
'Abschlussteile', 'unbekannte', 'Pferdemarkts', 'Tensorproduktes', 'Untersuchungsausschüssen', 'TeX', 'ungebetene', 'wasserdichtes', 'Albinos',
'übersetzendem', 'verrutschendem', 'Projektleiterinnen', 'verlustmachend', 'akzeptable', 'nichtzutreffende', 'zurückverlangten', 'erfolgloserer',
'anzukurbelndes', 'verkomplizierender', 'überrumpelnde', 'zurücktreibende', 'ungeklärteste', 'nacheiferndes', 'somatischem', 'lästerte', 'umsattelnd',
'zurückgezogener', 'sensitive', 'hinwirktet', 'Tagesordnungspunkten', 'aufrückenden', 'Konfitüre', 'Erwiderungen', 'Siebenschläfer', 'platter',
'hinzugerechnete', 'glasiertet', 'zuschütte', 'zuzurichtendes', 'Steuermitteln', 'zurückprallende', 'unsorgfältiger', 'Wirtssprachen', 'plagtest',
'apologetisches', 'aufbaust', 'Thermometerstand', 'wiederherstellst', 'fortschrittlicher', 'einzuprägende', 'Auflockerung', 'vorbeirennender',
'betagteren', 'unvorteilhafteren', 'Huaweis', 'Hotelbauprojekt', 'leistbar', 'einbestellender', 'eingewöhntem', 'Einzelfalls', 'errettetes',
'Ferienhinweise', 'Tokioters', 'Tablettenmissbrauchs', 'Ulla', 'Industriequalität', ];

/* source: https://bavaria-ipsum.de/, text under CC-by-sa licence */
const LIPSUM = [
    "Bavaria ipsum dolor sit amet Deandlgwand Charivari a geh a Ohrwaschl, a Jodler. Obacht um Godds wujn umananda baddscher Enzian pfiad de i mechad dee Schwoanshaxn. Vasteh Kuaschwanz nimmds Wiesn Vergeltsgott i hob di liab, Brezn. Jedza middn Graudwiggal no a Maß om auf’n Gipfe Stubn um Godds wujn, damischa. Gscheid Maibam und glei wirds no fui lustiga, boarischer wolpern measi gschmeidig! Radi oa des muas ma hoid kenna zua ja leck mi, Mamalad: Biagadn Spotzerl Gidarn Mamalad ham Wurscht jedza, Kirwa barfuaßat. Watschnbaam Fingahaggln Radler, Ohrwaschl Deandlgwand Brodzeid a ganze! Gamsbart Weißwiaschd gscheid a bissal, iwan Tisch ziagn hinter’m Berg san a no Leit zwoa hallelujah sog i! Mehra back mas auszutzeln, hoggd nia need Servas de spernzaln obandeln. Meidromml Almrausch gor, von.",
    "Weißwiaschd Schaung kost nix nia need ja mei, gscheid auf’d Schellnsau wo da Bartl an Most hoid fei di. Da a liabs Deandl gfreit mi a liabs Deandl Milli samma mehra. Obacht Radler auszutzeln, a ganze Hoiwe. Imma Maibam auf gehds beim Schichtl, Goaßmaß. Glacht umma bittschön, zua. I moan scho aa do legst di nieda gelbe Rüam nia an Heimatland san auf gehds beim Schichtl, hi gelbe Rüam! Sei im Beidl i moan oiwei an Weißwiaschd Bussal, noch da Giasinga Heiwog Baamwach ned de Sonn großherzig? Stubn a bissal wos gehd ollaweil Musi vui Fingahaggln Schmankal helfgod Hendl, ghupft wia gsprunga eam no! Luja Marei Blosmusi mei Meidromml Gamsbart, Habedehre! Fias gelbe Rüam spernzaln fei ned woar schnacksln, wo da Bartl an Most hoid. Wann griagd ma nacha wos z’dringa unbandig Engelgwand i mog di fei auszutzeln midanand.",
    "Gscheid sei obandeln, bittschön de Sonn wo hi is des liab Brotzeit Gaudi Spezi Semmlkneedl? Blosmusi geh da Kini, hawadere midananda Bladl glacht. Fias wui amoi hogg ma uns zamm, barfuaßat ja mei i hab an Brezn nimmds auf’d Schellnsau i bin a woschechta Bayer: Obfrettn geh Watschnbaam trihöleridi dijidiholleri, Gaudi so schee. A geh singan guad Wiesn soi soi, Gams Kaiwe sauba a liabs Deandl Schneid! I moan scho aa a bissal wos gehd ollaweil soi wea nia ausgähd, kummt nia hoam barfuaßat Kuaschwanz, Ramasuri amoi i waar soweid! Griaß God beinand großherzig des muas ma hoid kenna naa a Maß und no a Maß. Watschnbaam woaß woaß, Brotzeit Spezi wuid vui huift vui! Des wiad a Mordsgaudi mei aba Ledahosn a. Heid Biazelt mehra hea Biawambn sowos midanand pfundig, geh.",
    "Graudwiggal Xaver ognudelt auffi, helfgod Diandldrahn? Watschnpladdla Obazda a o’ha is, umananda. Mamalad oa aba i mechad dee Schwoanshaxn Maderln a liabs Deandl Oachkatzlschwoaf, gfreit mi. Nimma hoggd a ganze Hoiwe wolpern Prosd oans, zwoa, gsuffa Steckerleis a so a Schmarn Steckerleis. Middn iwan Tisch ziagn Stubn gscheit, auf gehds beim Schichtl ja, wo samma denn kimmt wia da Buachbinda Wanninger i do legst di nieda greaßt eich nachad. Gscheid ned woar a Hoiwe wea nia ausgähd, kummt nia hoam allerweil woaß wos Freibia. Resch wiavui Marterl Weiznglasl Fingahaggln hob do, Kneedl i daad Biagadn? Pfiad de Biakriagal gwihss Leonhardifahrt des, Ledahosn kloan Zidern i hob di liab und sei hea. Gschmeidig pfundig geh nia need gelbe Rüam, Haferl a geh kloan heitzdog Gamsbart helfgod.",
    "Gscheit imma Haberertanz a bravs Biakriagal Stubn hawadere midananda Schdarmbeaga See, do legst di nieda dringma aweng! Watschnpladdla anbandeln gscheit zwoa Engelgwand du dadst ma scho daugn a geh Namidog, hoam! Stubn hogg di hera geh glacht am acht’n Tag schuf Gott des Bia glacht Sepp kloan, gscheid. Kimmt wo da Bartl an Most hoid ned, sammawiedaguad! Sauba i moan scho aa Spotzerl Mamalad und nia need eam kloan mei Sauwedda, hod. Weiznglasl Kuaschwanz spernzaln samma: Um Godds wujn o’ha woaß kummd des is schee a bissal wos gehd ollaweil, Hemad bitt. Resch ned liberalitas Bavariae Kirwa woaß, etza nix Gwiass woass ma ned da? Wuid lem und lem lossn aasgem liberalitas Bavariae Oachkatzlschwoaf a bravs, wea nia ausgähd, kummt nia hoam Schdeckalfisch om auf’n Gipfe. Koa Graudwiggal midanand auf der Oim da gibt’s koa Sünd, hod Fingahaggln iwan Tisch ziagn Obazda.",
];


/**
 * fake a numeric ID by md5-ing it and converting it again to a decimal number
 */
function fakeId( $id ) {
    return hexdec( md5( $id ) );
}

/**
 * change all dates by a random date offset to the past
 *
 * Keep relative dates intact. Therefore, revisions stay sorted correctly.
 */
function fakeDate( $actualDate ) {
    global $dateOffset;
    $datetime = new DateTimeImmutable( $actualDate );
    return $datetime->sub( $dateOffset )->format( DateTimeInterface::ATOM );
}

/**
 * create a stable fake user name
 * 
 * Stable means, that the same input should provide the same fake output.
 */
function fakeUsername( $actualName, $type = 'name', $casedName = null ) {
    static $seenNames = [];
    $relevantName = ( $type === 'lowerName' && $casedName !== null ) ? $casedName : $actualName;
    if ( ! array_key_exists( $relevantName, $seenNames ) ) {
        $seenNames[ $relevantName ] = sprintf(
            '%s %s',
            FIRST_NAMES[array_rand( FIRST_NAMES, 1 )],
            LAST_NAMES[array_rand( LAST_NAMES, 1 )]);
    }
    $fakeName = $seenNames[ $relevantName ];
    if ( $type === 'lowerName' ) {
        $fakeName = strtolower( $fakeName );
    }
    return $fakeName;
}

/**
 * replace an email reproducibly with a fake example.com mail
 */
function fakeEmail( $actualEmail ) {
    return sprintf( '%s@example.com', md5( $actualEmail ) );
}

/**
 * reproducible fake titles
 * 
 * Hash the existing title, then split the hash in chunks of 2. Interpret those as hex to
 * fetch a TITLE_COMPONENTS entry.
 * 
 * The same original title will always result in the same fake title.
 */
function fakeTitle( $actualTitle, $type = 'title', $casedTitle = null ) {
    $relevantTitle = ( $type === 'lowerTitle' && $casedTitle !== null ) ? $casedTitle : $actualTitle;
    $hash = md5( $relevantTitle );
    $newTitleComponents = [];
    foreach ( str_split( $hash, 2 ) as $hex ) {
        $index = hexdec( $hex );
        $newTitleComponents[] = TITLE_COMPONENTS[ $index ];
        /* keep short titles short */
        if ( strlen( $relevantTitle ) < 30 && count( $newTitleComponents ) > 3 ) {
            break;
        } elseif ( strlen( $relevantTitle ) < 40 && count( $newTitleComponents ) > 4 ) {
            break;
        } elseif ( strlen( $relevantTitle ) < 50 && count( $newTitleComponents ) > 5 ) {
            break;
        }
    }
    $fakeTitle = join( ' ', $newTitleComponents );
    if ( $type === 'lowerTitle' ) {
        $fakeTitle = strtolower( $fakeTitle );
    }
    return $fakeTitle;
}

/**
 * replace all body content
 * 
 * Empty body content remains empty. Content length is somewhat retained by choosing an appropriate
 * amount of lorem ipsum sentences.
 * 
 * @todo do that more cleverly and try to keep some macro info
 */
function fakeContent( $actualContent, $class = 'BodyContent' ) {
    $dummy = '';
    for ( $i = 0; $i < count( LIPSUM ); $i++ ) {
        if ( strlen( $actualContent ) <= $i * 500 ) {
            break;
        }
        $dummy .= '<p>' . LIPSUM[ $i ] . '</p> ';
    }
    return $dummy;
}


$xml = file_get_contents($argv[1]);
$xsl = file_get_contents(__DIR__.'/anonymize-entities-xml.xslt');
$xmldoc = new DOMDocument();
$xmldoc->loadXML($xml);
$xsldoc = new DOMDocument();
$xsldoc->loadXML($xsl);

$proc = new XSLTProcessor();
$proc->registerPHPFunctions();
$proc->importStyleSheet($xsldoc);
echo $proc->transformToXML($xmldoc);
