import com.android.apksig.ApkVerifier;
import java.io.File;
public class VerifyGapps {
    public static void main(String[] args) throws Exception {
        boolean failed=false;
        for (int i = 0; i < args.length; i += 2) {
            String source = args[i];
            String path = args[i + 1];
            ApkVerifier.Result original = new ApkVerifier.Builder(new File(source))
                    .setMaxCheckedPlatformVersion(30).build().verify();
            ApkVerifier.Result r = new ApkVerifier.Builder(new File(path))
                    .setMaxCheckedPlatformVersion(30).build().verify();
            boolean valid = original.isVerified() && r.isVerified()
                    && original.getSignerCertificates().equals(r.getSignerCertificates());
            System.out.println((valid ? "PASS: " : "FAIL: ") + path);
            if (!valid) {
                System.out.println("Signature errors: " + r.getErrors());
                for (var s : r.getV1SchemeSigners()) System.out.println("v1 " + s.getErrors());
                for (var s : r.getV2SchemeSigners()) System.out.println("v2 " + s.getErrors());
                for (var s : r.getV3SchemeSigners()) System.out.println("v3 " + s.getErrors());
            }
            failed |= !valid;
        }
        if(failed) System.exit(1);
    }
}
