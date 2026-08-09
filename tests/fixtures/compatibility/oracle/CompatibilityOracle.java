import com.ft.restool.parser.ftm.FTMFile;
import com.ft.restool.parser.ftm.FTMParser;
import com.ft.restool.parser.prj.PRJReader;
import com.ft.restool.util.Crypter;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Base64;

public class CompatibilityOracle {
  private static String sha256(byte[] value) throws Exception {
    return java.util.HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value));
  }

  public static void main(String[] args) throws Exception {
    if (args.length != 1) throw new IllegalArgumentException("usage: CompatibilityOracle WORK_DIR");
    Path root = Path.of(args[0]).toRealPath();
    Path ftmPath = root.resolve("sample.ftm");
    Path prjPath = root.resolve("sample.prj");

    FTMParser parser = new FTMParser(ftmPath.toFile());
    FTMFile parsed = (FTMFile) parser.parse().values().iterator().next();
    String semanticJson = FTMParser.toJson(parsed);
    FTMFile fromJson = FTMParser.fromJson(semanticJson);
    boolean semanticEqual = JsonParser.parseString(semanticJson)
        .equals(JsonParser.parseString(FTMParser.toJson(fromJson)));
    Path jsonPath = root.resolve("sample.ftm.json");
    Files.writeString(jsonPath, semanticJson);
    new FTMParser(jsonPath.toFile()).store();
    byte[] stored = Files.readAllBytes(ftmPath);

    byte[] prjBefore = Files.readAllBytes(prjPath);
    PRJReader.write(PRJReader.read(prjPath.toFile()));
    byte[] prjAfter = Files.readAllBytes(prjPath);

    byte[] plain = Files.readAllBytes(root.resolve("set.plain"));
    byte[] encrypted = Crypter.encryptSetFileInMemory(plain);
    byte[] decrypted = Crypter.decryptSetFileInMemory(encrypted);

    byte[] dds = Files.readAllBytes(root.resolve("tex.dds"));
    byte[] encodedTex = Files.readAllBytes(root.resolve("tex.encoded"));
    byte[] transformed = Crypter.decryptTexFileInMemory(encodedTex);

    JsonObject output = new JsonObject();
    JsonObject ftm = new JsonObject();
    ftm.add("semantic", JsonParser.parseString(semanticJson));
    ftm.addProperty("roundTripSemantic", semanticEqual);
    ftm.addProperty("storedSha256", sha256(stored));
    output.add("ftm", ftm);
    JsonObject prj = new JsonObject();
    prj.addProperty("roundTripEqual", Arrays.equals(prjBefore, prjAfter));
    prj.addProperty("outputSha256", sha256(prjAfter));
    output.add("prj", prj);
    JsonObject set = new JsonObject();
    set.addProperty("roundTripEqual", Arrays.equals(plain, decrypted));
    set.addProperty("encryptedBase64", Base64.getEncoder().encodeToString(encrypted));
    output.add("set", set);
    JsonObject tex = new JsonObject();
    tex.addProperty("roundTripEqual", Arrays.equals(dds, transformed));
    tex.addProperty("transformedBase64", Base64.getEncoder().encodeToString(transformed));
    output.add("tex", tex);
    System.out.println(output);
  }
}
