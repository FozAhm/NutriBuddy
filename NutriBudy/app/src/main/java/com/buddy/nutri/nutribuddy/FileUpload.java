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

        import java.io.BufferedReader;
        import java.io.DataOutputStream;
        import java.io.IOException;
        import java.io.InputStreamReader;
        import java.net.Socket;

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
                    "http://172.30.177.39:8888");
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
        private final int PORT = 6123;
        private final String ADDRESS = "132.205.230.22:8888";
        private Socket client = null;
        private BufferedReader in = null;
        private DataOutputStream out = null;

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
         * Receive message from the server
         * @return
         */
        public String getMessage() {
            if (client != null) {
                try {
                    String fromServer = "";
                    String line;
                    while ((line = in.readLine()) != null) {
                        fromServer = line;
                        System.out.println("Server: " + fromServer);
                    }
                    return fromServer;
                } catch(IOException e) {
                    System.err.println("Failed to get: " + e.getMessage());
                }
            }
            System.err.println("Error: Client is null when message was received");
            return null;
        }

        /**
         * Send a message to the server
         * @param msg
         */
        public void sendMessage(String msg) {
            if(client != null) {
                try {
                    // Connected, so try sending a message to the server
                    out.writeUTF("Hi");
                } catch (IOException e) {
                    System.out.println("Failed to send " + e.getMessage());
                }
            } else {
                // Not connected to the server
                System.err.println("Send message failed: Client not connected.");
            }
        }
    }

//}