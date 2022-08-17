# BPS Circular API
How to use BPS Circular API & its functions

### Website status
For the website status:-

```
GET https://raj.moonball.io/bpsapi/v1/website/status
```

Returns JSON dict of `status` and `code`


### Latest circular
For the latest circular, two inputs are needed `category` and `receive`.

Where `category` is one of the following:-

- `ptm` - Returns PTM Circulars
- `general` - Returns General Circulars
- `exam` - Returns Exam Circulars

Where `receive` is one of the following:-

- `all` - Returns title and link as Circular
- `titles` - Returns title only
- `links` - Returns link only


```
GET root/circular/latest/{category}/{receive}
```

Returns JSON str of `titles` and/or `links` of Latest Circular

### List of circulars
For list of circulars, two inputs are needed `category` and `receive`.

Where `category` is one of the following:-

- `ptm` - Returns PTM Circulars
- `general` - Returns General Circulars
- `exam` - Returns Exam Circulars

Where `receive` is one of the following:-

- `all` - Returns titles and links
- `titles` - Returns titles only
- `links` - Returns links only

```
GET root/circular/list/{category}/{receive}
```

Returns JSON array of `titles` and/or `links` of Circulars
## Contributors
- Raj Dave
- Shanvanth Arunmozhi
- Muhammed Rayan

