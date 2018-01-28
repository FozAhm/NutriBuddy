package com.buddy.nutri.nutribuddy;

        import java.io.BufferedReader;
        import java.io.ByteArrayOutputStream;
        import java.io.InputStreamReader;

        import org.apache.http.HttpResponse;
        import org.apache.http.client.HttpClient;
        import org.apache.http.client.methods.HttpPost;
        import org.apache.http.entity.mime.HttpMultipartMode;
        import org.apache.http.entity.mime.MultipartEntity;
        import org.apache.http.entity.mime.content.ByteArrayBody;
        import org.apache.http.entity.mime.content.StringBody;
        import org.apache.http.impl.client.DefaultHttpClient;

        import android.app.Activity;
        import android.graphics.Bitmap;
        import android.graphics.Bitmap.CompressFormat;
        import android.graphics.BitmapFactory;
        import android.os.Bundle;
        import android.os.Environment;
        import android.util.Log;

public class FileUpload extends Activity{
    Bitmap bm;



    public void fileUpload() {
        Log.e("YO", "DOES THIS WORK");
        try {
            // bm = BitmapFactory.decodeResource(getResources(),
            // R.drawable.forest);
            bm = BitmapFactory.decodeFile(Environment.getExternalStorageDirectory().getPath()+"/Android/data/com.buddy.nutri.nutribudy/files/pic.jpg");
            executeMultipartPost();
        } catch (Exception e) {
            Log.e(e.getClass().getName(), e.getMessage());
        }
    }

    public void executeMultipartPost() throws Exception {
        try {
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            bm.compress(CompressFormat.JPEG, 75, bos);
            byte[] data = bos.toByteArray();
            HttpClient httpClient = new DefaultHttpClient();
            HttpPost postRequest = new HttpPost(
                    "http://172.30.177.39:5001/imageupload");
            ByteArrayBody bab = new ByteArrayBody(data, "pic.jpg");
            // File file= new File("/mnt/sdcard/forest.png");
            // FileBody bin = new FileBody(file);
            MultipartEntity reqEntity = new MultipartEntity(
                    HttpMultipartMode.BROWSER_COMPATIBLE);
            reqEntity.addPart("uploaded", bab);
            reqEntity.addPart("photoCaption", new StringBody("sfsdfsdf"));
            postRequest.setEntity(reqEntity);
            HttpResponse response = httpClient.execute(postRequest);
            BufferedReader reader = new BufferedReader(new InputStreamReader(
                    response.getEntity().getContent(), "UTF-8"));
            String sResponse;
            StringBuilder s = new StringBuilder();

            while ((sResponse = reader.readLine()) != null) {
                s = s.append(sResponse);
            }
            System.out.println("Response: " + s);
        } catch (Exception e) {
            // handle exception here
            Log.e(e.getClass().getName(), e.getMessage());
        }
    }
}