package com.buddy.nutri.nutribuddy;

        import java.io.BufferedReader;
        import java.io.ByteArrayOutputStream;
        import java.io.InputStreamReader;

        import java.io.BufferedReader;
        import java.io.DataOutputStream;
        import java.io.IOException;
        import java.io.InputStreamReader;
        import java.io.OutputStream;
        import java.net.Socket;

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

        import java.io.BufferedReader;
        import java.io.DataOutputStream;
        import java.io.IOException;
        import java.io.InputStreamReader;
        import java.net.Socket;

        import cz.msebera.android.httpclient.client.ClientProtocolException;

public class FileUpload extends Activity{
    Bitmap bm;



    public void fileUpload() {
        Log.e("YO", "DOES THIS WORK");
        try {
            // bm = BitmapFactory.decodeResource(getResources(),
            // R.drawable.forest);
            // bm = BitmapFactory.decodeFile(Environment.getExternalStorageDirectory().getPath()+"/Android/data/com.buddy.nutri.nutribudy/files/pic.jpg");
            
            
            Bitmap bm = BitmapFactory.decodeFile(Environment.getExternalStorageDirectory().getPath()+"/Android/data/com.buddy.nutri.nutribudy/files/pic.jpg");
            ByteArrayOutputStream baos = new ByteArrayOutputStream();  
            bm.compress(Bitmap.CompressFormat.JPEG, 100, baos); //bm is the bitmap object   
            byte[] b = baos.toByteArray(); executeMultipartPost();
        } 
        
        catch (Exception e) {
            Log.e(e.getClass().getName(), e.getMessage());
        }
    }
        private final int PORT = 80;
        private final String ADDRESS = "132.205.229.227";
        private Socket client = null;
        private BufferedReader in = null;
        private DataOutputStream out = null;

    public void fileUploadAndSend() throws IOException, ClientProtocolException {
        Socket socket = new Socket("localhost", 13085);
        OutputStream outputStream = socket.getOutputStream();

        //image to bw to array
        Bitmap bm = BitmapFactory.decodeFile(Environment.getExternalStorageDirectory().getPath()+"/Android/data/com.buddy.nutri.nutribudy/files/pic.jpg");
        ByteArrayOutputStream baos = new ByteArrayOutputStream();  
        bm.compress(Bitmap.CompressFormat.JPEG, 100, baos); //bm is the bitmap object   
        byte[] size = baos.toByteArray();
        //executeMultipartPost();

        outputStream.write(size);
        outputStream.write(baos.toByteArray());
        outputStream.flush();
        System.out.println("Flushed: " + System.currentTimeMillis());

        try {
            Thread.sleep(120000);
            System.out.println("Closing: " + System.currentTimeMillis());
            socket.close();
        }

         catch (InterruptedException e) {
            // Restore the interrupted status
            Thread.currentThread().interrupt();
        }
        }

    public void executeMultipartPost() throws Exception {
        try {
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            bm.compress(CompressFormat.JPEG, 75, bos);
            byte[] data = bos.toByteArray();
            HttpClient httpClient = new DefaultHttpClient();
            HttpPost postRequest = new HttpPost(
                    "http://132.205.230.22:8888");
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

            startTCP();

            while ((sResponse = reader.readLine()) != null) {
                s = s.append(sResponse);
            }
            System.out.println("Response: " + s);
        } catch (Exception e) {
            // handle exception here
            Log.e(e.getClass().getName(), e.getMessage());
        }
    }



    /**
     * TCP client to connect to LabView
     */
    //public class SocketClient {

        /**
         * Start the server and wait for incoming connections
         * @throws IOException
         */
        public void startTCP() throws IOException {
            client = new Socket(ADDRESS, PORT); // Connect to LabView server
            in = new BufferedReader(new InputStreamReader(client.getInputStream()));
            out = new DataOutputStream(client.getOutputStream());
        }
        /**
         * Send a message to the server
         * @param msg
         */
        // public class Send {

    }

//}