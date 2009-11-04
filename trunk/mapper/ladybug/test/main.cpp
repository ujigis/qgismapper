/******************************************************************************
 *   Copyright (c) 2009 Martin Dobias
 *
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation; either version 2 of the License, or
 *   (at your option) any later version.
 ******************************************************************************/

#include <QApplication>

#include "ladybug.h"
#include "ladywidget.h"

#include "ladybugwidget.h"

// capture test
int testCapture(int argc, char* argv[])
{
	QApplication a(argc, argv);
	
	Ladybug cam;
	
	if (!cam.init())
	{
    qDebug("ladybug init failed: %s", cam.errorMessage().toLocal8Bit().data());
		return 1;
	}

  LadyWidget w(cam, argv[2]);

	w.show();

	int res = a.exec();

	cam.exit();
	
	return res;
}

int testPlayer(int argc, char* argv[])
{
  QApplication a(argc, argv);
  
  LadybugWidget w;
  printf("open!\n");
  bool res = w.openStream(argv[2]);
  printf("open: %d\n", res);
  if (!res)
    return 2;
  w.show();
  printf("show\n");

  return a.exec();
}

int main(int argc, char* argv[])
{
  if (argc < 3)
  {
    fprintf(stderr, "Usage:\n  %s [p|c] file\nRun [p]layer or [c]apture.\n", argv[0]);
    return 1;
  }

  if (argv[1][0] == 'c')
    return testCapture(argc, argv);
  else if (argv[1][0] == 'p')
    return testPlayer(argc, argv);
  else
  {
    fprintf(stderr, "Unknown command.\n");
    return 1;
  }
}
